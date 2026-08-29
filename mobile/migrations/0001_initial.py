import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import mobile.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dispatch', '0003_alter_trip_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DispenseLog',
            fields=[
                ('id', models.CharField(default=mobile.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('station', models.CharField(blank=True, max_length=255)),
                ('product_type', models.CharField(blank=True, max_length=16)),
                ('opening_reading', models.IntegerField(default=0)),
                ('closing_reading', models.IntegerField(default=0)),
                ('volume_dispensed', models.IntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('photo', models.URLField(blank=True, null=True)),
                ('dispensed_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dispense_logs', to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dispense_logs', to='dispatch.trip')),
            ],
            options={
                'ordering': ['-dispensed_at'],
            },
        ),
        migrations.CreateModel(
            name='EmergencyContact',
            fields=[
                ('id', models.CharField(default=mobile.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=64, unique=True)),
                ('label', models.CharField(max_length=128)),
                ('phone_number', models.CharField(max_length=32)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('position', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['position', 'label'],
            },
        ),
        migrations.CreateModel(
            name='QuickReply',
            fields=[
                ('id', models.CharField(default=mobile.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('text', models.CharField(max_length=255, unique=True)),
                ('audience', models.CharField(choices=[('driver', 'driver'), ('inspector', 'inspector'), ('both', 'both')], default='both', max_length=10)),
                ('position', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['position', 'text'],
            },
        ),
        migrations.CreateModel(
            name='ReportReason',
            fields=[
                ('id', models.CharField(default=mobile.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=64, unique=True)),
                ('label', models.CharField(max_length=128)),
                ('position', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['position', 'label'],
            },
        ),
    ]
