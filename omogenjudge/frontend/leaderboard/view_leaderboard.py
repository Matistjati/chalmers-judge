import dataclasses
import math
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from django.db.models import Max
from django.http import HttpResponse

from omogenjudge.contests.archive_progress import problem_max_scores
from omogenjudge.storage.models import (
    Account,
    ContestGroupContest,
    ContestProblem,
    Problem,
    Submission,
    Verdict,
)
from omogenjudge.util.django_types import OmogenRequest
from omogenjudge.util.templates import render_template


@dataclasses.dataclass
class LeaderboardRow:
    rank: int
    username: str
    full_name: str
    solved: int


@dataclasses.dataclass
class LeaderboardArgs:
    rows: List[LeaderboardRow]
    total_problems: int


def _visible_problem_ids() -> Tuple[Set[int], Dict[int, float]]:
    archive_contest_ids = list(
        ContestGroupContest.objects
        .filter(contest__published=True)
        .values_list('contest_id', flat=True)
        .distinct()
    )
    contest_problems_qs = (
        ContestProblem.objects
        .filter(contest_id__in=archive_contest_ids)
        .select_related('problem', 'problem__current_version')
        .prefetch_related('problem__current_version__testgroups')
    )
    problems_by_id: Dict[int, Problem] = {}
    for cp in contest_problems_qs:
        if cp.problem_id not in problems_by_id:
            problems_by_id[cp.problem_id] = cp.problem
    max_scores = problem_max_scores(problems_by_id.values())
    return set(problems_by_id.keys()), max_scores


def view_leaderboard(request: OmogenRequest) -> HttpResponse:
    problem_ids, max_scores = _visible_problem_ids()

    best_rows = (
        Submission.objects
        .filter(problem_id__in=problem_ids)
        .values('account_id', 'problem_id')
        .annotate(best_score=Max('current_run__score'))
    )
    best_by_user: Dict[int, Dict[int, Optional[float]]] = defaultdict(dict)
    for r in best_rows:
        best_by_user[r['account_id']][r['problem_id']] = r['best_score']

    ac_rows = (
        Submission.objects
        .filter(problem_id__in=problem_ids, current_run__verdict=Verdict.AC)
        .values_list('account_id', 'problem_id')
        .distinct()
    )
    ac_by_user: Dict[int, Set[int]] = defaultdict(set)
    for account_id, problem_id in ac_rows:
        ac_by_user[account_id].add(problem_id)

    solves_by_user: Dict[int, int] = {}
    user_ids: Set[int] = set(best_by_user.keys()) | set(ac_by_user.keys())
    for uid in user_ids:
        solved_count = 0
        ac_set = ac_by_user.get(uid, set())
        bests = best_by_user.get(uid, {})
        candidate_pids = set(bests.keys()) | ac_set
        for pid in candidate_pids:
            if pid in ac_set:
                solved_count += 1
                continue
            best = bests.get(pid)
            max_score = max_scores.get(pid)
            if best is None or max_score is None or math.isinf(max_score):
                continue
            if best >= max_score:
                solved_count += 1
        if solved_count > 0:
            solves_by_user[uid] = solved_count

    accounts = Account.objects.filter(account_id__in=solves_by_user.keys()).only(
        'account_id', 'username', 'full_name'
    )
    accounts_by_id = {a.account_id: a for a in accounts}

    ordered = sorted(
        solves_by_user.items(),
        key=lambda kv: (-kv[1], accounts_by_id[kv[0]].username.lower()),
    )

    rows: List[LeaderboardRow] = []
    prev_solved: Optional[int] = None
    prev_rank = 0
    for idx, (uid, solved) in enumerate(ordered, start=1):
        account = accounts_by_id[uid]
        if solved != prev_solved:
            prev_rank = idx
            prev_solved = solved
        rows.append(LeaderboardRow(
            rank=prev_rank,
            username=account.username,
            full_name=account.full_name,
            solved=solved,
        ))

    return render_template(
        request,
        'leaderboard/view_leaderboard.html',
        LeaderboardArgs(rows=rows, total_problems=len(problem_ids)),
    )
