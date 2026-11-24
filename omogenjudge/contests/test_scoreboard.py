import datetime
from types import SimpleNamespace

from django.test import TestCase

from omogenjudge.contests.scoreboard import (
    BinaryWithPenalty,
    ImportedTeamEntry,
    _IMPORTED_START,
    _ImportedRun,
    _ImportedSubmissionEntry,
    freeze_start,
)
from omogenjudge.storage.models import Account, Contest, ImportedTeam, ScoringType, Status, Team, TeamMember, \
    Verdict

HOUR = datetime.timedelta(hours=1)


class FreezeTest(TestCase):

    def setUp(self):
        self.contest = Contest.objects.create(
            title='Contest', short_name='c', duration=5 * HOUR, freeze_duration=HOUR,
            scoring_type=ScoringType.BINARY_WITH_PENALTY, only_virtual_contest=True)
        self.problem = SimpleNamespace(problem_id=1, label='A',
                                       problem=SimpleNamespace(current_version=SimpleNamespace(scoring=False)))

    def _imported(self, name, *solve_times):
        team = ImportedTeam.objects.create(contest=self.contest, team_name=name, source='src')
        return ImportedTeamEntry(imported_team=team, submissions=[
            _ImportedSubmissionEntry(problem_id=1, date_created=_IMPORTED_START + t,
                                     current_run=_ImportedRun(verdict=Verdict.AC))
            for t in solve_times])

    def _results(self, teams, submissions=(), **kwargs):
        board = BinaryWithPenalty(self.contest, [self.problem], teams, now=_IMPORTED_START + 6 * HOUR,
                                  at_time=5 * HOUR, **kwargs)
        board.process_submissions(list(submissions))
        return {t.team.display_name(): t.results[0] for t in board.scoreboard_teams}

    def test_freeze_start(self):
        self.assertIsNone(freeze_start(self.contest, 3 * HOUR))
        self.assertEqual(4 * HOUR, freeze_start(self.contest, 4 * HOUR))
        self.assertEqual(4 * HOUR, freeze_start(self.contest, 4.5 * HOUR))
        self.assertIsNone(freeze_start(self.contest, 5 * HOUR))
        self.assertIsNone(freeze_start(self.contest, None))
        self.contest.freeze_duration = None
        self.assertIsNone(freeze_start(self.contest, 4.5 * HOUR))

    def test_frozen_submissions_are_pending(self):
        teams = [self._imported('early', 3 * HOUR), self._imported('late', 4.5 * HOUR)]
        results = self._results(teams, frozen_since=4 * HOUR)
        self.assertTrue(results['early'].accepted)
        self.assertFalse(results['late'].accepted)
        self.assertEqual(1, results['late'].pending)

        results = self._results(teams)
        self.assertTrue(results['late'].accepted)

    def test_own_team_is_not_frozen(self):
        account = Account.objects.create(username='me', email='me@example.com', full_name='Me')
        team = Team.objects.create(contest=self.contest, team_name='mine', practice=True,
                                   contest_start_time=_IMPORTED_START)
        TeamMember.objects.create(team=team, account=account)
        submission = SimpleNamespace(
            account_id=account.account_id, problem_id=1, date_created=_IMPORTED_START + 4.5 * HOUR,
            current_run=SimpleNamespace(status=Status.DONE, verdict=Verdict.AC))
        frozen = self._results([team], [submission], frozen_since=4 * HOUR)
        self.assertEqual(1, frozen['mine'].pending)
        live = self._results([team], [submission], frozen_since=4 * HOUR, freeze_exempt_team_id=team.team_id)
        self.assertTrue(live['mine'].accepted)
