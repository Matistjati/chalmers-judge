# Generated by Django 4.1.6 on 2024-03-26 23:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0008_contest_try_penalty'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='allow_only_python',
            field=models.BooleanField(default=False),
        ),
    ]
