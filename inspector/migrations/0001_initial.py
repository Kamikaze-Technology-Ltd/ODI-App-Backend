import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import inspector.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dispatch', '0003_alter_trip_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='InspectorProfile',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('badge_id', models.CharField(default=inspector.models.generate_badge_id, max_length=20, unique=True)),
                ('rank', models.CharField(choices=[('inspector', 'Inspector'), ('senior_inspector', 'Senior Inspector'), ('lead_inspector', 'Lead Inspector')], default='inspector', max_length=32)),
                ('zone', models.CharField(blank=True, max_length=255)),
                ('depot', models.CharField(blank=True, max_length=255)),
                ('clearance_level', models.PositiveIntegerField(default=1)),
                ('vehicles_cleared', models.PositiveIntegerField(default=0)),
                ('is_on_duty', models.BooleanField(default=False)),
                ('is_verified', models.BooleanField(default=False)),
                ('active_since', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='inspector_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('label', models.CharField(default='Morning Shift', max_length=64)),
                ('depot', models.CharField(blank=True, max_length=255)),
                ('zone', models.CharField(blank=True, max_length=255)),
                ('terminal', models.CharField(blank=True, max_length=255)),
                ('role_label', models.CharField(default='Inspector - Clearance & Response', max_length=128)),
                ('clearance_level', models.PositiveIntegerField(default=1)),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('start_time', models.TimeField(blank=True, null=True)),
                ('end_time', models.TimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('assigned', 'assigned'), ('active', 'active'), ('ended', 'ended')], default='assigned', max_length=10)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('inspector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-created_at']},
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('reference', models.CharField(default=inspector.models.generate_alert_reference, max_length=20, unique=True)),
                ('alert_type', models.CharField(choices=[('distress', 'distress'), ('incident', 'incident')], default='distress', max_length=10)),
                ('category', models.CharField(choices=[('spillage', 'spillage'), ('security', 'security'), ('breakdown', 'breakdown'), ('other', 'other')], default='other', max_length=12)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('message', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('received', 'received'), ('responding', 'responding'), ('monitoring', 'monitoring'), ('help_on_way', 'help_on_way'), ('escalated', 'escalated'), ('resolved', 'resolved')], default='received', max_length=12)),
                ('location', models.CharField(blank=True, max_length=255)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('photo', models.URLField(blank=True, null=True)),
                ('inspector_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='raised_alerts', to=settings.AUTH_USER_MODEL)),
                ('inspector', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_alerts', to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alerts', to='dispatch.trip')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AlertEvent',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('label', models.CharField(max_length=128)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('occurred_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline', to='inspector.alert')),
            ],
            options={'ordering': ['occurred_at']},
        ),
        migrations.CreateModel(
            name='InspectorQuery',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('sent', 'sent'), ('acknowledged', 'acknowledged'), ('answered', 'answered')], default='sent', max_length=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_queries', to=settings.AUTH_USER_MODEL)),
                ('inspector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_queries', to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspector_queries', to='dispatch.trip')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AppNotification',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField(blank=True)),
                ('category', models.CharField(choices=[('general', 'general'), ('command_center', 'command_center'), ('dispatch', 'dispatch'), ('distress', 'distress'), ('loading', 'loading'), ('clearance', 'clearance'), ('query', 'query')], default='general', max_length=20)),
                ('reference', models.CharField(blank=True, max_length=64)),
                ('is_read', models.BooleanField(default=False)),
                ('is_important', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='app_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.CharField(default=inspector.models.generate_id, max_length=255, primary_key=True, serialize=False)),
                ('distress_calls', models.BooleanField(default=True)),
                ('loading_events', models.BooleanField(default=True)),
                ('dispatch_confirmations', models.BooleanField(default=True)),
                ('vibration', models.BooleanField(default=True)),
                ('email_notifications', models.BooleanField(default=False)),
                ('in_app_only', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
