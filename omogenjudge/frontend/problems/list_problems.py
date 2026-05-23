import dataclasses
import math
from typing import Dict, List, Optional

from django.db.models import Prefetch
from django.http import HttpResponse

from omogenjudge.contests.archive_progress import (
    problem_max_scores,
    user_best_scores,
    user_solved_problem_ids,
)
from omogenjudge.contests.scoreboard import ScoreboardMaker, ScoreboardTeam, load_scoreboard
from omogenjudge.frontend.decorators import only_started_contests
from omogenjudge.storage.models import (
    Contest,
    ContestGroupContest,
    ContestProblem,
    Problem,
    ProblemStatement,
)
from omogenjudge.util.django_types import OmogenRequest
from omogenjudge.util.templates import render_template


@only_started_contests
def list_problems(request: OmogenRequest) -> HttpResponse:
    if request.contest:
        return list_contest_problems(request, request.contest)
    return list_archive_problems(request)


@dataclasses.dataclass
class ContestProblemArgs:
    scoreboard: ScoreboardMaker
    team_results: Optional[ScoreboardTeam] = None


@only_started_contests
def list_contest_problems(request: OmogenRequest, contest: Contest) -> HttpResponse:
    user = request.user
    scoreboard = load_scoreboard(contest)
    args = ContestProblemArgs(scoreboard=scoreboard)
    if user.is_authenticated:
        user_id = user.account_id
        if user_id in scoreboard.best_user_result:
            args.team_results = scoreboard.best_user_result[user_id]
    return render_template(request, 'problems/contest_problems.html', args)


@dataclasses.dataclass
class ArchiveProblemRow:
    problem: Problem
    contest_short_name: str
    contest_title: str
    contest_label: str
    max_score: float
    solved: bool = False
    best_score: Optional[float] = None


@dataclasses.dataclass
class ArchiveProblemsArgs:
    rows: List[ArchiveProblemRow]
    show_progress: bool


def list_archive_problems(request: OmogenRequest) -> HttpResponse:
    archive_contest_ids = list(
        ContestGroupContest.objects
        .filter(contest__published=True)
        .values_list('contest_id', flat=True)
        .distinct()
    )
    contest_problems_qs = (
        ContestProblem.objects
        .filter(contest_id__in=archive_contest_ids)
        .select_related('contest', 'problem', 'problem__current_version')
        .prefetch_related('problem__current_version__testgroups')
        .prefetch_related(Prefetch(
            'problem__statements',
            ProblemStatement.objects.all().only('problem_id', 'language', 'title')))
        .order_by('contest__title', 'label', 'problem__short_name')
    )

    # Dedup by problem: keep first contest seen (sorted by contest title).
    seen: Dict[int, ContestProblem] = {}
    for cp in contest_problems_qs:
        if cp.problem_id not in seen:
            seen[cp.problem_id] = cp

    problems = [cp.problem for cp in seen.values()]
    max_scores = problem_max_scores(problems)

    show_progress = request.user.is_authenticated
    solved: set[int] = set()
    best_scores: Dict[int, Optional[float]] = {}
    if show_progress:
        problem_ids = list(seen.keys())
        solved = user_solved_problem_ids(request.user, problem_ids, max_scores)
        best_scores = user_best_scores(request.user, problem_ids)

    rows: List[ArchiveProblemRow] = []
    for pid, cp in seen.items():
        max_score = max_scores.get(pid, 0.0)
        rows.append(ArchiveProblemRow(
            problem=cp.problem,
            contest_short_name=cp.contest.short_name,
            contest_title=cp.contest.title,
            contest_label=cp.label or '',
            max_score=0.0 if math.isinf(max_score) else max_score,
            solved=pid in solved,
            best_score=best_scores.get(pid),
        ))

    return render_template(request, 'problems/archive_problems.html',
                           ArchiveProblemsArgs(rows=rows, show_progress=show_progress))
