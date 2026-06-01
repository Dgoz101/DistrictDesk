import csv
from datetime import timedelta

from django.contrib import messages
from django.http import StreamingHttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin

from .checkout_service import try_checkout
from .csv_io import EXPORT_FIELDNAMES, iter_export_rows, parse_upload, run_import
from .forms import DeviceCheckoutForm, DeviceForm
from .models import Device
from .qr import qr_svg_data_uri, report_url_for_device

MAX_PRINT_SELECTION = 50


class _Echo:
    """Writer for StreamingHttpResponse CSV."""

    def write(self, value):
        return value


class DeviceExportCsvView(AdminRequiredMixin, View):
    """Streaming CSV export of all devices."""

    def get(self, request):
        qs = Device.objects.select_related(
            'device_type', 'status', 'assigned_user', 'location'
        ).order_by('asset_tag')

        def rows():
            yield EXPORT_FIELDNAMES
            for row in iter_export_rows(qs):
                yield [row.get(h, '') for h in EXPORT_FIELDNAMES]

        pseudo_buffer = _Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(r) for r in rows()),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = 'attachment; filename="devices_export.csv"'
        return response


class DeviceImportView(AdminRequiredMixin, View):
    """GET: upload form. POST: parse CSV and import (optional dry_run=1)."""

    template_name = 'devices/device_import.html'

    def get(self, request):
        return render(request, self.template_name, {'result': None})

    def post(self, request):
        dry = request.POST.get('dry_run') == '1' or request.GET.get('dry_run') == '1'
        f = request.FILES.get('file')
        if not f:
            messages.error(request, 'Choose a CSV file to upload.')
            return render(request, self.template_name, {'result': None})
        _fieldnames, rows = parse_upload(f)
        if rows:
            keys_lower = {k.lower() for k in rows[0].keys()}
            missing = [h for h in EXPORT_FIELDNAMES if h not in keys_lower]
            if missing:
                messages.warning(
                    request,
                    f'CSV is missing recommended columns (import may still proceed): {", ".join(missing)}',
                )
        result = run_import(rows, dry_run=dry)
        if dry:
            messages.info(request, 'Dry run — no rows were saved.')
        else:
            messages.success(
                request,
                f'Import finished: {result["created"]} created, {result["updated"]} updated.',
            )
        if result['errors']:
            messages.warning(request, f'{len(result["errors"])} row(s) had errors.')
        return render(request, self.template_name, {'result': result, 'dry_run': dry})


class DevicePrintBulkView(AdminRequiredMixin, View):
    """Print asset-tag labels for multiple devices (POST `device_ids` from list)."""

    def post(self, request):
        raw = request.POST.getlist('device_ids')
        ids = []
        seen = set()
        for x in raw:
            if len(ids) >= MAX_PRINT_SELECTION:
                break
            try:
                pk = int(x)
            except (ValueError, TypeError):
                continue
            if pk not in seen:
                seen.add(pk)
                ids.append(pk)
        if not ids:
            messages.warning(request, 'Select at least one device, then click Print selected.')
            return redirect('devices:list')
        qs = Device.objects.filter(pk__in=ids).select_related(
            'device_type', 'status', 'assigned_user', 'location'
        )
        by_id = {d.pk: d for d in qs}
        devices = [by_id[i] for i in ids if i in by_id]
        if not devices:
            messages.warning(request, 'No valid devices were selected.')
            return redirect('devices:list')
        label_ctx = []
        for d in devices:
            url = report_url_for_device(request, d)
            label_ctx.append({'device': d, 'report_url': url, 'qr_data_uri': qr_svg_data_uri(url)})
        return render(request, 'devices/device_print_bulk.html', {'label_items': label_ctx})


class DevicePrintLabelView(AdminRequiredMixin, DetailView):
    """Printable asset-tag label (administrators only)."""

    model = Device
    template_name = 'devices/device_print_label.html'
    context_object_name = 'device'

    def get_queryset(self):
        return Device.objects.select_related(
            'device_type', 'status', 'assigned_user', 'location'
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        url = report_url_for_device(self.request, self.object)
        ctx['report_url'] = url
        ctx['qr_data_uri'] = qr_svg_data_uri(url)
        return ctx


class DeviceListView(AdminRequiredMixin, ListView):
    """Device inventory list (FR-26); administrators only."""
    model = Device
    template_name = 'devices/device_list.html'
    context_object_name = 'devices'
    paginate_by = 25

    def get_queryset(self):
        qs = Device.objects.select_related(
            'device_type', 'status', 'assigned_user', 'location'
        ).order_by('asset_tag')
        raw = self.request.GET.get('warranty_within', '').strip()
        if raw.isdigit():
            days = int(raw)
            if days > 0:
                today = timezone.localdate()
                end = today + timedelta(days=days)
                qs = qs.filter(
                    warranty_end_date__isnull=False,
                    warranty_end_date__gte=today,
                    warranty_end_date__lte=end,
                )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['warranty_within'] = self.request.GET.get('warranty_within', '').strip()
        q = self.request.GET.copy()
        q.pop('page', None)
        ctx['filter_query'] = q.urlencode()
        return ctx


class DeviceDetailView(AdminRequiredMixin, DetailView):
    """Device detail, checkout history, loaner checkout / return."""

    model = Device
    template_name = 'devices/device_detail.html'
    context_object_name = 'device'

    def get_queryset(self):
        return Device.objects.select_related(
            'device_type', 'status', 'assigned_user', 'location'
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        device = self.object
        ctx['checkouts'] = device.checkouts.select_related(
            'checked_out_to', 'created_by'
        ).prefetch_related(
            'fines__fine_type',
        ).order_by('-checked_out_at')[:50]
        ctx['open_checkout'] = device.checkouts.filter(returned_at__isnull=True).first()
        ctx['checkout_form'] = DeviceCheckoutForm()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        if action == 'checkout':
            form = DeviceCheckoutForm(request.POST)
            if form.is_valid():
                co, err = try_checkout(
                    device=self.object,
                    checked_out_to=form.cleaned_data['checked_out_to'],
                    due_at=form.cleaned_data.get('due_at'),
                    notes=form.cleaned_data.get('notes') or '',
                    created_by=request.user,
                )
                if err:
                    messages.error(request, err)
                else:
                    messages.success(request, 'Checkout recorded.')
                return redirect('devices:detail', pk=self.object.pk)
            messages.error(request, 'Fix the checkout form errors.')
            ctx = self.get_context_data(object=self.object)
            ctx['checkout_form'] = form
            return render(request, self.template_name, ctx)

        return redirect('devices:detail', pk=self.object.pk)


class DeviceCreateView(AdminRequiredMixin, CreateView):
    """Create a device record (FR-27)."""
    model = Device
    form_class = DeviceForm
    template_name = 'devices/device_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Device created.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('devices:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = 'Add device'
        ctx['submit_label'] = 'Create device'
        return ctx


class DeviceUpdateView(AdminRequiredMixin, UpdateView):
    """Edit a device record (FR-27)."""
    model = Device
    form_class = DeviceForm
    template_name = 'devices/device_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Device updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('devices:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_title'] = f'Edit device: {self.object.asset_tag}'
        ctx['submit_label'] = 'Save changes'
        return ctx


class PublicDeviceReportView(DetailView):
    """Read-only device summary for hallway QR stickers (no login)."""
    model = Device
    template_name = 'devices/device_public_report.html'
    context_object_name = 'device'
    slug_field = 'public_report_uuid'
    slug_url_kwarg = 'report_uuid'

    def get_queryset(self):
        return Device.objects.select_related('device_type', 'status', 'location')

    def get_context_data(self, **kwargs):
        from urllib.parse import urlencode

        ctx = super().get_context_data(**kwargs)
        dev = self.object
        ticket_path = f'{reverse("tickets:create")}?device={dev.pk}'
        ctx['open_ticket_url'] = ticket_path
        ctx['open_ticket_login_url'] = f'{reverse("accounts:login")}?{urlencode({"next": ticket_path})}'
        return ctx
