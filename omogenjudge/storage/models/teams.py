from django.db import models

from omogenjudge.storage.models import Account, Contest, Problem
from omogenjudge.storage.models.submissions import Verdict
from omogenjudge.util import django_fields
from omogenjudge.util.django_fields import EnumField


class Team(models.Model):
    team_id = models.AutoField(primary_key=True)
    contest = models.ForeignKey(Contest, models.CASCADE)
    team_name = django_fields.TextField(null=True, blank=True)
    team_data = models.JSONField(blank=True, default=dict)
    # When this team starts the contest
    contest_start_time = models.DateTimeField(null=True, blank=True)
    practice = models.BooleanField(null=False, default=False)

    def display_name(self) -> str:
        if self.team_name:
            return self.team_name
        team_members = self.teammember_set.select_related("account").all()
        if team_members:
            return ', '.join(team_member.account.full_name for team_member in team_members)
        return 'Empty team'

    def __str__(self):
        return self.display_name() + " (in " + str(self.contest) + ")"

    class Meta:
        db_table = 'team'


class TeamMember(models.Model):
    team_member_id = models.AutoField(primary_key=True)
    team = models.ForeignKey(Team, models.CASCADE)
    account = models.ForeignKey(Account, models.CASCADE)

    class Meta:
        db_table = 'team_member'
        unique_together = (('team', 'account'),)


class ImportedTeam(models.Model):
    """A team whose results were imported from another judge, e.g. the onsite contest a mirror replays.

    Imported teams have no accounts; their submissions live in ImportedSubmission and are merged into
    the scoreboard, including virtual replays.
    """
    imported_team_id = models.AutoField(primary_key=True)
    contest = models.ForeignKey(Contest, models.CASCADE)
    team_name = django_fields.TextField()
    affiliation = django_fields.TextField(null=True, blank=True)
    # Short label shown next to the team on the scoreboard, e.g. "BAPC 2026".
    source = django_fields.TextField()
    # The team's id on the other judge.
    external_id = django_fields.TextField(null=True, blank=True)

    def display_name(self) -> str:
        return self.team_name

    def __str__(self):
        return self.team_name + " (imported into " + str(self.contest) + ")"

    class Meta:
        db_table = 'imported_team'
        unique_together = (('contest', 'external_id'),)


class ImportedSubmission(models.Model):
    imported_submission_id = models.AutoField(primary_key=True)
    imported_team = models.ForeignKey(ImportedTeam, models.CASCADE)
    problem = models.ForeignKey(Problem, models.CASCADE)
    # Seconds from the team's contest start.
    contest_time_seconds = models.IntegerField()
    verdict = EnumField(enum_type=Verdict)
    # False if the time was estimated rather than known, e.g. a rejected try when only final standings were known.
    time_is_exact = models.BooleanField(default=True)

    class Meta:
        db_table = 'imported_submission'
