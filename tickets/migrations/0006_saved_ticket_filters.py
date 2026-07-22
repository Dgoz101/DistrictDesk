from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tickets', '0005_ticket_relations'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedTicketFilter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                (
                    'params',
                    models.JSONField(
                        default=dict,
                        help_text='Ticket list query parameters (location, status, sort, etc.).',
                    ),
                ),
                (
                    'is_default',
                    models.BooleanField(
                        default=False,
                        help_text='When set, apply this filter on login and when opening the ticket list.',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='saved_ticket_filters',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'tickets_savedticketfilter',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='savedticketfilter',
            index=models.Index(fields=['user', 'is_default'], name='tickets_sav_user_id_def_idx'),
        ),
        migrations.AddConstraint(
            model_name='savedticketfilter',
            constraint=models.UniqueConstraint(
                fields=('user', 'name'),
                name='tickets_savedticketfilter_user_name_uniq',
            ),
        ),
    ]
