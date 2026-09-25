from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0012_contest_count_shots'),
    ]

    operations = [
        migrations.RenameField(
            model_name='problemversion',
            old_name='memory_limit_kb',
            new_name='memory_limit_mib',
        ),
        # Memory limits were stored as the problem.yaml limit (in MiB) times 1000.
        migrations.RunSQL(
            sql='UPDATE problem_version SET memory_limit_mib = memory_limit_mib / 1000',
            reverse_sql='UPDATE problem_version SET memory_limit_mib = memory_limit_mib * 1000',
        ),
    ]
