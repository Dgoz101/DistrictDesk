from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import AdminRequiredMixin

from .forms import (
    TicketAdminUpdateForm,
    TicketAssignForm,
    TicketCommentForm,
    TicketForm,
)
from .models import Ticket, TicketAssignment, TicketComment
from .services import apply_admin_ticket_update, assign_ticket, record_ticket_created


class TicketListView(LoginRequiredMixin, ListView):
    """List tickets: own tickets for standard users; all tickets + filters for admins (FR-14, FR-23–FR-25)."""
    model = Ticket
    template_name = 'tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 25

    def get_queryset(self):
        qs = Ticket.objects.select_related(
            'category', 'priority', 'submitter', 'device', 'location'
        ).prefetch_related(
            Prefetch(
                'assignments',
                queryset=TicketAssignment.objects.filter(is_current=True).select_related(
                    'assigned_to'
                ),
            )
        )

        if not self.request.user.is_administrator:
            return qs.filter(submitter=self.request.user).order_by('-created_at')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category_id=category)

        priority = self.request.GET.get('priority')
        if priority:
            qs = qs.filter(priority_id=priority)

        assigned = self.request.GET.get('assigned')
        if assigned:
            qs = qs.filter(
                assignments__assigned_to_id=assigned,
                assignments__is_current=True,
            ).distinct()

        sort = self.request.GET.get('sort', '-created_at')
        if sort == 'priority':
            qs = qs.order_by('priority__sort_order', '-created_at')
        elif sort == '-priority':
            qs = qs.order_by('-priority__sort_order', '-created_at')
        elif sort == 'status':
            qs = qs.order_by('status', '-created_at')
        elif sort == '-status':
            qs = qs.order_by('-status', '-created_at')
        elif sort == 'created_at':
            qs = qs.order_by('created_at')
        else:
            qs = qs.order_by('-created_at')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['scope_all_tickets'] = user.is_administrator
        get = self.request.GET.copy()
        if 'page' in get:
            del get['page']
        ctx['filter_query'] = get.urlencode()
        if user.is_administrator:
            from django.contrib.auth import get_user_model

            from .models import TicketCategory, PriorityLevel

            ctx['filter_categories'] = TicketCategory.objects.all()
            ctx['filter_priorities'] = PriorityLevel.objects.all()
            ctx['filter_users'] = get_user_model().objects.filter(is_active=True).order_by(
                'username'
            )
            ctx['status_choices'] = Ticket.Status.choices
        return ctx


class TicketCreateView(LoginRequiredMixin, CreateView):
    """Submit a new ticket (FR-10–FR-13)."""
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/ticket_form.html'

    def form_valid(self, form):
        form.instance.submitter = self.request.user
        form.instance.status = Ticket.Status.OPEN
        with transaction.atomic():
            response = super().form_valid(form)
            record_ticket_created(self.object, self.request.user)
        messages.success(self.request, 'Your support ticket was submitted.')
        return response

    def get_success_url(self):
        return reverse('tickets:detail', kwargs={'pk': self.object.pk})


class TicketDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Ticket detail with status history (FR-15–FR-17); admin actions (Phase 4)."""
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    raise_exception = True

    def get_queryset(self):
        return Ticket.objects.select_related(
            'category', 'priority', 'submitter', 'device', 'location'
        ).prefetch_related(
            'status_history__changed_by',
            'comments__author',
            Prefetch(
                'assignments',
                queryset=TicketAssignment.objects.filter(is_current=True).select_related(
                    'assigned_to', 'assigned_by'
                ),
            ),
        )

    def test_func(self):
        ticket = self.get_object()
        user = self.request.user
        return ticket.submitter_id == user.id or user.is_administrator

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ticket = self.object
        ctx['current_assignment'] = ticket.assignments.filter(is_current=True).first()
        if self.request.user.is_administrator:
            ctx['admin_update_form'] = TicketAdminUpdateForm(instance=ticket)
            ctx['assign_form'] = TicketAssignForm()
            ctx['comment_form'] = TicketCommentForm()
        return ctx


class TicketAdminUpdateView(AdminRequiredMixin, View):
    """POST: update status, priority, category (FR-19–FR-20, FR-22)."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        old_status = ticket.status
        form = TicketAdminUpdateForm(request.POST, instance=ticket)
        if form.is_valid():
            cd = form.cleaned_data
            apply_admin_ticket_update(
                ticket,
                request.user,
                category=cd['category'],
                priority=cd['priority'],
                new_status=cd['status'],
                old_status=old_status,
            )
            messages.success(request, 'Ticket updated.')
        else:
            messages.error(request, 'Could not update ticket. Please check the fields.')
        return redirect('tickets:detail', pk=pk)


class TicketAssignView(AdminRequiredMixin, View):
    """POST: assign ticket to a user (FR-18)."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        form = TicketAssignForm(request.POST)
        if form.is_valid():
            assign_ticket(ticket, form.cleaned_data['assigned_to'], request.user)
            messages.success(request, 'Assignment updated.')
        else:
            messages.error(request, 'Could not assign ticket. Choose a valid user.')
        return redirect('tickets:detail', pk=pk)


class TicketCommentAddView(AdminRequiredMixin, View):
    """POST: add comment or internal note (FR-21)."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        form = TicketCommentForm(request.POST)
        if form.is_valid():
            TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=form.cleaned_data['body'],
                is_internal=form.cleaned_data['is_internal'],
            )
            messages.success(request, 'Comment added.')
        else:
            messages.error(request, 'Could not add comment.')
        return redirect('tickets:detail', pk=pk)
