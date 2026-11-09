from django.db import migrations, models
import django.db.models.deletion
import omogenjudge.storage.models.submissions
import omogenjudge.util.django_fields


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0013_problemversion_memory_limit_mib'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubmissionCaseFeedback',
            fields=[
                ('submission_case_feedback_id', models.AutoField(primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField()),
                ('time_usage_ms', models.IntegerField()),
                ('verdict', omogenjudge.util.django_fields.EnumField(enum_type=omogenjudge.storage.models.submissions.Verdict)),
                ('team_output', models.BinaryField(blank=True, null=True)),
                ('team_output_truncated', models.BooleanField(default=False)),
                ('team_error', models.BinaryField(blank=True, null=True)),
                ('team_error_truncated', models.BooleanField(default=False)),
                ('validator_message', models.BinaryField(blank=True, null=True)),
                ('exit_code', models.IntegerField(blank=True, null=True)),
                ('exit_signal', models.IntegerField(blank=True, null=True)),
                ('problem_testcase', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='+', to='storage.problemtestcase')),
                ('submission_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='case_feedback', to='storage.submissionrun')),
            ],
            options={
                'db_table': 'submission_case_feedback',
            },
        ),
    ]
