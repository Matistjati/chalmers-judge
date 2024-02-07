from django.db import transaction
from django.utils import timezone

from omogenjudge.storage.models import Account, Contest, Team, TeamMember
from omogenjudge.teams.lookup import contest_team_for_user


class TeamExists(Exception): pass


def register_user_for_practice(contest: Contest, user: Account):
    with transaction.atomic():
        if contest_team_for_user(contest, user):
            raise TeamExists()
        team = Team(contest=contest, practice=True)
        team.save()
        TeamMember(team=team, account=user).save()


def register_user_for_virtual(contest: Contest, user: Account):
    with transaction.atomic():
        if contest_team_for_user(contest, user):
            raise TeamExists()
        team = Team(contest=contest, practice=True, contest_start_time=timezone.now())
        team.save()
        TeamMember(team=team, account=user).save()
    
def register_user_for_ongoing(contest: Contest, user: Account):
    with transaction.atomic():
        if contest_team_for_user(contest, user):
            raise TeamExists()
        
        contest_start_time=contest.start_time # Per default, do not get extra time for late signup
        if contest.flexible_start_window_end_time: # If we have flexible start window, the duration is based off of this
            contest_start_time = timezone.now()
            
        team = Team(contest=contest, practice=False, contest_start_time=contest_start_time)
        team.save()
        TeamMember(team=team, account=user).save()
