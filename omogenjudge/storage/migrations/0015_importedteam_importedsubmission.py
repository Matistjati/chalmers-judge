from django.db import migrations, models
import django.db.models.deletion
import omogenjudge.storage.models.submissions
import omogenjudge.util.django_fields


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0014_submissioncasefeedback'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportedTeam',
            fields=[
                ('imported_team_id', models.AutoField(primary_key=True, serialize=False)),
                ('team_name', omogenjudge.util.django_fields.TextField()),
                ('affiliation', omogenjudge.util.django_fields.TextField(blank=True, null=True)),
                ('source', omogenjudge.util.django_fields.TextField()),
                ('external_id', omogenjudge.util.django_fields.TextField(blank=True, null=True)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.contest')),
            ],
            options={
                'db_table': 'imported_team',
                'unique_together': {('contest', 'external_id')},
            },
        ),
        migrations.CreateModel(
            name='ImportedSubmission',
            fields=[
                ('imported_submission_id', models.AutoField(primary_key=True, serialize=False)),
                ('contest_time_seconds', models.IntegerField()),
                ('verdict', omogenjudge.util.django_fields.EnumField(enum_type=omogenjudge.storage.models.submissions.Verdict)),
                ('time_is_exact', models.BooleanField(default=True)),
                ('imported_team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.importedteam')),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.problem')),
            ],
            options={
                'db_table': 'imported_submission',
            },
        ),
    ]
