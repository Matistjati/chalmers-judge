import dataclasses
import math
from typing import Dict, Iterable, Optional

from django.db.models import Max

from omogenjudge.problems.testgroups import get_subtask_scores
from omogenjudge.storage.models import (
    Account,
    Contest,
    ContestGroup,
    Problem,
    Submission,
    Verdict,
)


@dataclasses.dataclass
class ArchiveProgress:
    solved: int = 0
    total: int = 0

    @property
    def pct(self) -> Optional[float]:
        if self.total == 0:
            return None
        return self.solved / self.total * 100


def problem_max_scores(problems: Iterable[Problem]) -> Dict[int, float]:
    out: Dict[int, float] = {}
    for p in problems:
        out[p.problem_id] = sum(get_subtask_scores(p.current_version))
    return out


def user_solved_problem_ids(
    user: Account,
    problem_ids: Iterable[int],
    max_scores: Dict[int, float],
) -> set[int]:
    pid_list = list(problem_ids)
    if not pid_list:
        return set()
    rows = (
        Submission.objects
        .filter(account=user, problem_id__in=pid_list)
        .values('problem_id')
        .annotate(best_score=Max('current_run__score'))
    )
    best_by_problem: Dict[int, Optional[float]] = {
        r['problem_id']: r['best_score'] for r in rows
    }
    ac_problem_ids = set(
        Submission.objects
        .filter(account=user, problem_id__in=pid_list, current_run__verdict=Verdict.AC)
        .values_list('problem_id', flat=True)
        .distinct()
    )
    solved: set[int] = set()
    for pid in pid_list:
        if pid in ac_problem_ids:
            solved.add(pid)
            continue
        best = best_by_problem.get(pid)
        max_score = max_scores.get(pid)
        if best is None or max_score is None or math.isinf(max_score):
            continue
        if best >= max_score:
            solved.add(pid)
    return solved


def user_best_scores(user: Account, problem_ids: Iterable[int]) -> Dict[int, Optional[float]]:
    pid_list = list(problem_ids)
    if not pid_list:
        return {}
    rows = (
        Submission.objects
        .filter(account=user, problem_id__in=pid_list)
        .values('problem_id')
        .annotate(best_score=Max('current_run__score'))
    )
    return {r['problem_id']: r['best_score'] for r in rows}


def collect_problem_ids_for_contest(contest: Contest) -> set[int]:
    return set(contest.contestproblem_set.values_list('problem_id', flat=True))


def collect_problem_ids_for_group(group: ContestGroup) -> set[int]:
    ids: set[int] = set()
    for sub in group.subgroups:
        ids |= collect_problem_ids_for_group(sub)
    for cgc in group.subcontests:
        ids |= collect_problem_ids_for_contest(cgc.contest)
    return ids


def progress_from_solved_set(problem_ids: Iterable[int], solved: set[int]) -> ArchiveProgress:
    pids = set(problem_ids)
    return ArchiveProgress(solved=len(pids & solved), total=len(pids))
