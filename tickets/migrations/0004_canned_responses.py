from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_ticket_sla'),
    ]

    operations = [
        migrations.CreateModel(
            name='CannedResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('body', models.TextField(help_text='Text inserted into the comment field when selected.')),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'tickets_cannedresponse',
                'ordering': ['sort_order', 'title'],
            },
        ),
    ]
