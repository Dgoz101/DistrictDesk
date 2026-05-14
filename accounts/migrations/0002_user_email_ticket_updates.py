from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_ticket_updates',
            field=models.BooleanField(
                default=True,
                help_text='When enabled, receive email when your tickets are updated by staff.',
            ),
        ),
    ]
