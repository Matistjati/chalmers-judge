import dataclasses
from typing import Dict, Optional

from django.db.models import Prefetch
from django.http import Http404, HttpResponse

from omogenjudge.contests.archive_progress import (
    ArchiveProgress,
    collect_problem_ids_for_contest,
    collect_problem_ids_for_group,
    problem_max_scores,
    progress_from_solved_set,
    user_solved_problem_ids,
)
from omogenjudge.contests.contest_groups import groups_by_shortnames, root_contest_groups
from omogenjudge.storage.models import (
    Contest,
    ContestGroup,
    ContestGroupContest,
    Problem,
    Team,
)
from omogenjudge.teams.lookup import contest_team_for_user
from omogenjudge.util.django_types import OmogenRequest
from omogenjudge.util.templates import render_template


@dataclasses.dataclass
class ArchiveContest:
    contest: ContestGroupContest
    my_team: Optional[Team] = None
    progress: Optional[ArchiveProgress] = None


@dataclasses.dataclass
class ArchiveGroupEntry:
    group: ContestGroup
    progress: Optional[ArchiveProgress] = None


@dataclasses.dataclass
class ArchiveArgs:
    current_groups: list[ContestGroup]
    groups: list[ArchiveGroupEntry]
    contests: list[ArchiveContest]


def view_archive(request: OmogenRequest, group_path: Optional[str] = None) -> HttpResponse:
    if group_path:
        try:
            current_groups = groups_by_shortnames(group_path.split("/"))
        except ContestGroup.DoesNotExist:
            raise Http404
        groups = current_groups[-1].subgroups
        contests = [ArchiveContest(
            contest=cgc,
            my_team=contest_team_for_user(cgc.contest, request.user)
        )
            for cgc in current_groups[-1].subcontests
        ]
    else:
        current_groups = []
        groups = root_contest_groups()
        contests = []

    groups.sort(key=lambda group: -group.order)

    group_entries = [ArchiveGroupEntry(group=g) for g in groups]

    if request.user.is_authenticated:
        group_problem_ids: Dict[int, set[int]] = {
            g.contest_group_id: collect_problem_ids_for_group(g) for g in groups
        }
        contest_problem_ids: Dict[int, set[int]] = {
            ac.contest.contest_id: collect_problem_ids_for_contest(ac.contest.contest)
            for ac in contests
        }
        all_problem_ids: set[int] = set()
        for ids in group_problem_ids.values():
            all_problem_ids |= ids
        for ids in contest_problem_ids.values():
            all_problem_ids |= ids
        if all_problem_ids:
            problems = list(Problem.objects
                            .filter(problem_id__in=all_problem_ids)
                            .select_related('current_version')
                            .prefetch_related('current_version__testgroups'))
            max_scores = problem_max_scores(problems)
            solved = user_solved_problem_ids(request.user, all_problem_ids, max_scores)
        else:
            solved = set()
        for entry in group_entries:
            entry.progress = progress_from_solved_set(
                group_problem_ids[entry.group.contest_group_id], solved)
        for ac in contests:
            ac.progress = progress_from_solved_set(
                contest_problem_ids[ac.contest.contest_id], solved)

    return render_template(request, 'archive/view_archive.html',
                           ArchiveArgs(current_groups, group_entries, contests))
