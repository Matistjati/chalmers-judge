from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0015_importedteam_importedsubmission'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='freeze_duration',
            field=models.DurationField(blank=True, null=True),
        ),
    ]
