# Generated by Django 4.1.6 on 2023-02-11 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0005_contestgroup_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='practice',
            field=models.BooleanField(default=False),
        ),
    ]
