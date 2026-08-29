"""Make driver-only Profile fields optional.

The Profile table was designed around drivers, so `license_expiry`,
`drivers_license`, `medical_history`, `gender`, `date_of_birth` and
`emergency_contact_phone_no` were all NOT NULL with no default. Inspector
signup has none of those values, so every POST /api/inspector/signup/ died with
an IntegrityError on `license_expiry`. These fields are now nullable/blank.

Phone columns are also widened from 13 to 20 characters to match
`User.phone_number`, which already allowed 20.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("athens", "0014_profile_start_date_profile_supervisor_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="license_expiry",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="profile",
            name="drivers_license",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="profile",
            name="medical_history",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="profile",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("male", "male"), ("female", "female")],
                default="",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="profile",
            name="emergency_contact_phone_no",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AlterField(
            model_name="profile",
            name="phone_number",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name="profile",
            name="profile_picture",
            field=models.URLField(blank=True, null=True),
        ),
    ]
