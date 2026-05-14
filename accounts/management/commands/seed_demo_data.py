"""
Create rich demo data: users, locations, devices, and tickets (CSE499 / README).

Requires: migrate, seed_roles, seed_ticket_lookups, seed_device_lookups.

By default creates demo accounts if missing. Password for each account is the
part of the email before ``@`` (e.g. ``admin@demo.test`` → password ``admin``).

Re-run: mostly idempotent via get_or_create; ticket workflow steps skip if already done.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, User
from core.models import Location
from devices.models import Device, DeviceType, DeviceStatus
from tickets.models import Ticket, TicketAssignment, TicketCategory, PriorityLevel, TicketComment
from tickets.services import apply_admin_ticket_update, assign_ticket, record_ticket_created


def _password_from_email(email: str) -> str:
    """Use the local part of the address as the demo password."""
    return email.split('@', 1)[0].lower()


def _ensure_user(email: str, *, role_name: str, is_staff: bool = False, is_superuser: bool = False):
    """
    Get or create a user with username and email set to ``email``.
    On create, password is set to ``_password_from_email(email)``.
    """
    role = Role.objects.get(name=role_name)
    user, created = User.objects.get_or_create(
        username=email,
        defaults={
            'email': email,
            'role': role,
            'is_staff': is_staff,
            'is_superuser': is_superuser,
            'is_active': True,
        },
    )
    if created:
        user.set_password(_password_from_email(email))
        user.save()
    else:
        updates = []
        if user.role_id != role.id:
            user.role = role
            updates.append('role')
        if user.email != email:
            user.email = email
            updates.append('email')
        if updates:
            user.save(update_fields=updates)
    return user, created


class Command(BaseCommand):
    help = (
        'Create demo users/locations/devices/tickets (requires seed_* lookups). '
        'Default password rule: local-part of email before @.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin',
            default='admin@demo.test',
            help='Primary administrator username (email) for scripted ticket actions',
        )
        parser.add_argument(
            '--user',
            default='user@demo.test',
            help='Primary standard user username (email) for scripted tickets',
        )
        parser.add_argument(
            '--no-create-users',
            action='store_true',
            help='Do not create demo users; use existing accounts (see --admin / --user)',
        )

    def handle(self, *args, **options):
        admin_username = options['admin']
        user_username = options['user']
        create_users = not options['no_create_users']

        demo_admin_emails = [
            'admin@demo.test',
            'it.admin@districtdesk.local',
            'sysadmin@districtdesk.local',
        ]
        demo_standard_emails = [
            'user@demo.test',
            'teacher1@districtdesk.local',
            'frontdesk@districtdesk.local',
            'student1@districtdesk.local',
        ]

        if admin_username not in demo_admin_emails:
            demo_admin_emails.insert(0, admin_username)
        if user_username not in demo_standard_emails:
            demo_standard_emails.insert(0, user_username)

        with transaction.atomic():
            if create_users:
                created_any = []
                for i, email in enumerate(demo_admin_emails):
                    _, c = _ensure_user(
                        email,
                        role_name='Administrator',
                        is_staff=(i == 0),
                        is_superuser=(i == 0),
                    )
                    if c:
                        created_any.append(email)
                for email in demo_standard_emails:
                    _, c = _ensure_user(email, role_name='Standard User')
                    if c:
                        created_any.append(email)
                if created_any:
                    self.stdout.write(
                        self.style.NOTICE(
                            'Created demo users (password = part before @): '
                            + ', '.join(created_any)
                        )
                    )
            else:
                try:
                    User.objects.get(username=admin_username)
                except User.DoesNotExist:
                    self.stderr.write(
                        self.style.ERROR(
                            f'Admin user not found: {admin_username!r}. '
                            'Omit --no-create-users or create that user first.'
                        )
                    )
                    raise SystemExit(1)
                try:
                    User.objects.get(username=user_username)
                except User.DoesNotExist:
                    self.stderr.write(
                        self.style.ERROR(
                            f'Standard user not found: {user_username!r}. '
                            'Omit --no-create-users or create that user first.'
                        )
                    )
                    raise SystemExit(1)

            admin = User.objects.get(username=admin_username)
            std = User.objects.get(username=user_username)

            def U(email: str, fallback: User) -> User:
                try:
                    return User.objects.get(username=email)
                except User.DoesNotExist:
                    return fallback

            it_admin = U('it.admin@districtdesk.local', admin)
            sysadmin = U('sysadmin@districtdesk.local', admin)
            teacher = U('teacher1@districtdesk.local', std)
            frontdesk = U('frontdesk@districtdesk.local', std)
            student1 = U('student1@districtdesk.local', std)

            loc_specs = [
                ('Main Office', 'District IT main desk.'),
                ('Library', 'Student study area and printers.'),
                ('Gymnasium', 'Athletics AV and scoreboard systems.'),
                ('Computer Lab 101', 'CTE classroom lab.'),
                ('District Office', 'Administration building.'),
            ]
            locations = {}
            for name, desc in loc_specs:
                loc, _ = Location.objects.get_or_create(name=name, defaults={'description': desc})
                locations[name] = loc

            loc_main = locations['Main Office']
            loc_lab = locations['Computer Lab 101']
            loc_lib = locations['Library']

            def dtype(name):
                o, _ = DeviceType.objects.get_or_create(name=name)
                return o

            def dstatus(name):
                o, _ = DeviceStatus.objects.get_or_create(name=name)
                return o

            dt_laptop = dtype('Laptop')
            dt_desktop = dtype('Desktop')
            dt_printer = dtype('Printer')
            dt_tablet = dtype('Tablet')

            ds_in = dstatus('In-service')
            ds_checkout = dstatus('Checked-out')
            ds_repair = dstatus('Repair')
            ds_retired = dstatus('Retired')

            device_specs = [
                ('DEMO-1001', dt_laptop, ds_in, 'Dell Latitude 5440', 'SN-LAP-1001', std, loc_main),
                ('DEMO-1002', dt_desktop, ds_in, 'HP Elite Mini', 'SN-DT-2002', teacher, loc_lab),
                ('DEMO-1003', dt_printer, ds_repair, 'Canon imageRUNNER', 'SN-PR-3003', None, loc_lib),
                ('DEMO-1004', dt_tablet, ds_checkout, 'iPad (cart set)', 'SN-TB-4004', None, loc_lib),
                ('DEMO-1005', dt_laptop, ds_in, 'Lenovo ThinkPad', 'SN-LAP-5005', it_admin, loc_main),
                ('DEMO-1006', dt_desktop, ds_retired, 'Legacy lab PC', 'SN-DT-6006', None, loc_lab),
                (
                    'DEMO-1007',
                    dt_printer,
                    ds_in,
                    'Brother HL-L2395',
                    'SN-PR-7007',
                    None,
                    locations['District Office'],
                ),
                ('DEMO-1008', dt_laptop, ds_in, 'Surface Laptop', 'SN-LAP-8008', frontdesk, locations['Gymnasium']),
            ]

            devices = {}
            for asset_tag, dtp, st, model, serial, assigned, loc in device_specs:
                d, _ = Device.objects.get_or_create(
                    asset_tag=asset_tag,
                    defaults={
                        'device_type': dtp,
                        'status': st,
                        'model': model,
                        'serial_number': serial,
                        'assigned_user': assigned,
                        'location': loc,
                    },
                )
                devices[asset_tag] = d

            d1 = devices['DEMO-1001']

            cat = TicketCategory.objects.order_by('sort_order', 'name').first()
            pri_low = PriorityLevel.objects.order_by('sort_order', 'name').first()
            pri_high = PriorityLevel.objects.order_by('-sort_order', '-name').first() or pri_low
            if not cat or not pri_low:
                self.stderr.write(
                    self.style.ERROR(
                        'Missing TicketCategory or PriorityLevel. Run: python manage.py seed_ticket_lookups'
                    )
                )
                raise SystemExit(1)

            ticket_defs = [
                (
                    '[Demo] Printer not working',
                    'Printer in main office is jammed.',
                    std,
                    None,
                    loc_main,
                    'x123',
                    pri_high,
                ),
                (
                    '[Demo] Laptop will not boot',
                    'Blue screen on startup.',
                    std,
                    d1,
                    loc_main,
                    user_username,
                    pri_high,
                ),
                (
                    '[Demo] Lab PCs drop Wi‑Fi',
                    'Intermittent disconnects during class blocks.',
                    teacher,
                    devices['DEMO-1002'],
                    loc_lab,
                    'room 101',
                    pri_low,
                ),
                (
                    '[Demo] New staff onboarding',
                    'Need accounts and email for a substitute teacher.',
                    frontdesk,
                    None,
                    locations['District Office'],
                    'front desk',
                    pri_low,
                ),
                (
                    '[Demo] Tablet cart will not charge',
                    'Cart B in library; several devices not charging.',
                    student1,
                    devices['DEMO-1004'],
                    loc_lib,
                    'student helpdesk',
                    pri_high,
                ),
                (
                    '[Demo] SSO timeout after password change',
                    'Staff report repeated sign-in prompts after directory password change.',
                    frontdesk,
                    None,
                    loc_main,
                    'ext 555',
                    pri_low,
                ),
            ]

            for title, desc, submitter, dev, loc, contact, priority in ticket_defs:
                t, created = Ticket.objects.get_or_create(
                    title=title,
                    defaults={
                        'description': desc,
                        'category': cat,
                        'priority': priority,
                        'submitter': submitter,
                        'device': dev,
                        'location': loc,
                        'contact_info': contact,
                    },
                )
                if created:
                    record_ticket_created(t, submitter)

            # Scripted workflow on the laptop ticket (assign → comment → resolve)
            t2 = Ticket.objects.get(title='[Demo] Laptop will not boot')
            if not TicketAssignment.objects.filter(ticket=t2, is_current=True).exists():
                assign_ticket(t2, admin, admin)
            TicketComment.objects.get_or_create(
                ticket=t2,
                author=admin,
                body='Investigating; likely disk failure.',
                defaults={'is_internal': True},
            )
            if t2.status != Ticket.Status.RESOLVED:
                old = t2.status
                apply_admin_ticket_update(
                    t2,
                    admin,
                    category=cat,
                    priority=pri_high,
                    new_status=Ticket.Status.RESOLVED,
                    old_status=old,
                )

            # Second ticket: assign to IT admin, leave in workflow for filters
            t_lab = Ticket.objects.get(title='[Demo] Lab PCs drop Wi‑Fi')
            if not TicketAssignment.objects.filter(ticket=t_lab, is_current=True).exists():
                assign_ticket(t_lab, it_admin, it_admin)

            t_sso = Ticket.objects.get(title='[Demo] SSO timeout after password change')
            if not TicketAssignment.objects.filter(ticket=t_sso, is_current=True).exists():
                assign_ticket(t_sso, sysadmin, admin)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: users={User.objects.count()} locations={Location.objects.count()} "
                f"devices={Device.objects.count()} tickets={Ticket.objects.count()}"
            )
        )
        self.stdout.write(
            self.style.NOTICE(
                'Demo passwords are the email local-part before @ '
                '(example: admin@demo.test → admin). '
                'First demo admin (admin@demo.test) has Django superuser for /admin/.'
            )
        )
