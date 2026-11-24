import dataclasses

from django.http import HttpResponse
from django.utils import timezone

from omogenjudge.contests.scoreboard import ScoreboardMaker, freeze_start, load_scoreboard
from omogenjudge.frontend.decorators import requires_contest
from omogenjudge.storage.models import Contest
from omogenjudge.teams.lookup import contest_team_for_user
from omogenjudge.util.django_types import OmogenRequest
from omogenjudge.util.templates import render_template


@dataclasses.dataclass
class ScoreboardArgs:
    scoreboard: ScoreboardMaker


@requires_contest
def view_scoreboard(request: OmogenRequest, contest: Contest) -> HttpResponse:
    my_team = contest_team_for_user(contest, request.user)
    now = timezone.now()
    at_time = None
    # The viewer's contest clock, which decides whether the scoreboard is frozen for them.
    elapsed = None
    if my_team and my_team.contest_start_time:
        elapsed = now - my_team.contest_start_time
        if elapsed <= contest.duration:
            at_time = elapsed
    elif (contest.start_time and not contest.flexible_start_window_end_time and not contest.only_virtual_contest
          and not request.user.is_superuser):
        elapsed = now - contest.start_time
    scoreboard = load_scoreboard(
        contest, now=now, at_time=at_time,
        frozen_since=freeze_start(contest, elapsed),
        freeze_exempt_team_id=my_team.team_id if my_team else None)
    return render_template(request, 'scoreboard/view_scoreboard.html', ScoreboardArgs(scoreboard))
