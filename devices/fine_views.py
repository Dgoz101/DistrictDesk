from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin

from .fine_service import (
    add_fines_to_checkout,
    calculate_late_fee,
    parse_fine_lines_from_post,
    return_checkout_with_fines,
)
from .forms import AddCheckoutFinesForm
from .models import Device, DeviceCheckout, DeviceCheckoutPolicy, DeviceFine, DeviceFineType


class DeviceFineListView(AdminRequiredMixin, ListView):
    """All device fines with status filter."""
    model = DeviceFine
    template_name = 'devices/fine_list.html'
    context_object_name = 'fines'
    paginate_by = 50

    def get_queryset(self):
        qs = DeviceFine.objects.select_related(
            'checkout__device',
            'checkout__checked_out_to',
            'fine_type',
            'assessed_by',
        ).order_by('-assessed_at')
        status = self.request.GET.get('status', '').strip()
        if status in dict(DeviceFine.Status.choices):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_filter'] = self.request.GET.get('status', '').strip()
        ctx['status_choices'] = DeviceFine.Status.choices
        q = self.request.GET.copy()
        if 'page' in q:
            del q['page']
        ctx['filter_query'] = q.urlencode()
        return ctx


class DeviceReturnInspectionView(AdminRequiredMixin, View):
    """Separate return page: condition check, damage fines, late fee."""
    template_name = 'devices/device_return_inspection.html'

    def get_device(self, pk):
        return get_object_or_404(
            Device.objects.select_related('device_type', 'status'),
            pk=pk,
        )

    def get_open_checkout(self, device):
        return (
            device.checkouts.filter(returned_at__isnull=True)
            .select_related('checked_out_to')
            .first()
        )

    def get(self, request, pk):
        device = self.get_device(pk)
        checkout = self.get_open_checkout(device)
        if not checkout:
            messages.info(request, 'This device has no open checkout.')
            return redirect('devices:detail', pk=device.pk)
        policy = DeviceCheckoutPolicy.get_solo()
        late = calculate_late_fee(checkout, policy)
        fine_types = DeviceFineType.objects.filter(is_active=True).exclude(
            code__in=('late_return',)
        ).order_by('sort_order', 'name')
        return render(
            request,
            self.template_name,
            {
                'device': device,
                'checkout': checkout,
                'policy': policy,
                'late_preview': late,
                'fine_types': fine_types,
            },
        )

    def post(self, request, pk):
        device = self.get_device(pk)
        checkout = self.get_open_checkout(device)
        if not checkout:
            messages.info(request, 'This device has no open checkout.')
            return redirect('devices:detail', pk=device.pk)

        policy = DeviceCheckoutPolicy.get_solo()
        late = calculate_late_fee(checkout, policy)
        set_repair = request.POST.get('set_repair_status') == '1'

        no_damage = request.POST.get('condition') == 'no_damage'
        apply_late = request.POST.get('apply_late_fee') == '1'
        if no_damage and not apply_late:
            lines = []
        else:
            lines = parse_fine_lines_from_post(request.POST, late_preview=late)

        co = return_checkout_with_fines(
            device=device,
            actor=request.user,
            fine_lines=lines,
            set_repair_status=set_repair,
        )
        if not co:
            messages.error(request, 'Could not complete return.')
            return redirect('devices:detail', pk=device.pk)

        total = co.fine_total
        if total > 0:
            messages.success(
                request,
                f'Device returned. Fines recorded: ${total:.2f} total.',
            )
        else:
            messages.success(request, 'Device returned with no fines.')
        return redirect('devices:detail', pk=device.pk)


class DeviceCheckoutAddFinesView(AdminRequiredMixin, View):
    """Add damage fines to an already-returned checkout."""
    template_name = 'devices/device_add_fines.html'

    def get(self, request, pk, checkout_pk):
        device = get_object_or_404(Device, pk=pk)
        checkout = get_object_or_404(
            DeviceCheckout.objects.select_related('checked_out_to'),
            pk=checkout_pk,
            device=device,
        )
        if checkout.returned_at is None:
            messages.error(request, 'Use return inspection while the device is still checked out.')
            return redirect('devices:detail', pk=device.pk)
        fine_types = DeviceFineType.objects.filter(is_active=True).exclude(
            code__in=('late_return',)
        ).order_by('sort_order', 'name')
        return render(
            request,
            self.template_name,
            {
                'device': device,
                'checkout': checkout,
                'fine_types': fine_types,
                'form': AddCheckoutFinesForm(),
            },
        )

    def post(self, request, pk, checkout_pk):
        device = get_object_or_404(Device, pk=pk)
        checkout = get_object_or_404(DeviceCheckout, pk=checkout_pk, device=device)
        if checkout.returned_at is None:
            messages.error(request, 'Cannot add fines to an open checkout.')
            return redirect('devices:detail', pk=device.pk)

        lines = parse_fine_lines_from_post(request.POST, late_preview=None)
        n = add_fines_to_checkout(checkout=checkout, actor=request.user, fine_lines=lines)
        if n:
            messages.success(request, f'Added {n} fine line(s).')
        else:
            messages.info(request, 'No fines were added.')
        return redirect('devices:detail', pk=device.pk)
