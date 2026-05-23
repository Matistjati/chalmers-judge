import dataclasses
from typing import Dict, Optional

from django.db.models import Prefetch
from django.http import HttpResponse

from omogenjudge.frontend.decorators import only_started_contests, requires_contest, requires_user
from omogenjudge.frontend.submissions.view_submission import ProblemWithScores, SubmissionWithSubtasks
from omogenjudge.problems.lookup import contest_problems_with_grading
from omogenjudge.problems.testgroups import get_submission_subtask_scores, get_subtask_scores
from omogenjudge.storage.models import Account, Contest, ContestProblem, Problem, ProblemStatement
from omogenjudge.submissions.lookup import list_queue_submissions
from omogenjudge.util.django_types import OmogenRequest
from omogenjudge.util.templates import render_template

GLOBAL_QUEUE_LIMIT = 200


@dataclasses.dataclass
class QueueArgs:
    submissions: list[SubmissionWithSubtasks]
    problems: Dict[int, ProblemWithScores]


@dataclasses.dataclass
class GlobalQueueArgs:
    submissions: list[SubmissionWithSubtasks]
    problems: Dict[int, ProblemWithScores]
    problem_contest_short_name: Dict[int, Optional[str]]


@requires_user(only_superuser=True)
def global_queue(request: OmogenRequest, user: Account) -> HttpResponse:
    submissions = list(list_queue_submissions(None, None)[:GLOBAL_QUEUE_LIMIT])
    problem_ids = list({s.problem_id for s in submissions})
    problems_qs = (Problem.objects
                   .filter(problem_id__in=problem_ids)
                   .select_related('current_version')
                   .prefetch_related('current_version__testgroups')
                   .prefetch_related(Prefetch('statements',
                                              ProblemStatement.objects.all().only('problem_id', 'language', 'title'))))
    problem_map: Dict[int, ProblemWithScores] = {
        p.problem_id: ProblemWithScores(problem=p, subtask_scores=get_subtask_scores(p.current_version))
        for p in problems_qs
    }
    problem_contest_short_name: Dict[int, Optional[str]] = {pid: None for pid in problem_ids}
    for cp in (ContestProblem.objects
               .filter(problem_id__in=problem_ids)
               .select_related('contest')
               .order_by('contest_id')):
        if problem_contest_short_name.get(cp.problem_id) is None:
            problem_contest_short_name[cp.problem_id] = cp.contest.short_name

    submissions_with_subtasks = [
        SubmissionWithSubtasks(
            sub,
            get_submission_subtask_scores(
                list(sub.current_run.group_runs.all()),
                subtasks=len(problem_map[sub.problem_id].subtask_scores))
        )
        for sub in submissions if sub.problem_id in problem_map
    ]
    return render_template(request, 'submissions/global_queue.html',
                           GlobalQueueArgs(submissions_with_subtasks, problem_map, problem_contest_short_name))


@requires_user(only_superuser=True)
@requires_contest
def submission_queue(request: OmogenRequest, user: Account, contest: Contest) -> HttpResponse:
    # TODO: add page for non-contests
    problems = [
        ProblemWithScores(problem=cp.problem, subtask_scores=get_subtask_scores(cp.problem.current_version))
        for cp in contest_problems_with_grading(contest)]

    problem_map = {p.problem.problem_id: p for p in problems}

    submissions = list_queue_submissions(None, list(problem_map.keys()))
    submissions_with_subtasks = [
        SubmissionWithSubtasks(
            submission,
            get_submission_subtask_scores(list(submission.current_run.group_runs.all()),
                                          subtasks=len(problem_map[submission.problem_id].subtask_scores))
        )
        for
        submission in submissions]

    return render_template(request, 'submissions/queue.html', QueueArgs(submissions_with_subtasks, problem_map))


@requires_user()
@requires_contest
@only_started_contests
def my_submissions(request: OmogenRequest, user: Account, contest: Contest) -> HttpResponse:
    # TODO: add page for non-contests
    problems = [
        ProblemWithScores(problem=cp.problem, subtask_scores=get_subtask_scores(cp.problem.current_version))
        for cp in contest_problems_with_grading(contest)]

    problem_map = {p.problem.problem_id: p for p in problems}

    submissions = list_queue_submissions([user.account_id], list(problem_map.keys()))
    submissions_with_subtasks = [
        SubmissionWithSubtasks(submission, get_submission_subtask_scores(list(submission.current_run.group_runs.all()),
                                                                         subtasks=len(problem_map[
                                                                                          submission.problem_id].subtask_scores)))
        for
        submission in submissions]

    return render_template(request, 'submissions/my.html', QueueArgs(submissions_with_subtasks, problem_map))
