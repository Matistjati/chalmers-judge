import logging
import sys
from pathlib import Path

from django.core.management import BaseCommand
from problemtools.context import Context
from problemtools.diagnostics import LoggingDiagnostics, VerifyError
from problemtools.model import load_problem
from problemtools.verifyproblem import ProblemVerifier

import omogenjudge.storage.models
from omogenjudge.problems.install import install_problem
from omogenjudge.util.console import ask_yes_or_no
from omogenjudge.problems.lookup import problem_by_name

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Installs a new problem'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, nargs='+')
        parser.add_argument('--ignore-warnings', action='store_true')

    def handle(self, *args, **options):
        for path in options['path']:
            probdir = Path(path).resolve()
            logger.info("Installing problem at path %s", probdir)
            diagnostics = LoggingDiagnostics.create(probdir.name)
            try:
                problem = load_problem(probdir, diagnostics)
            except VerifyError:
                logger.error("Could not load problem: exiting")
                sys.exit(1)

            try:
                problem_by_name(problem.shortname)
                if not ask_yes_or_no("Problem already exists: update it (y/N)?", False):
                    sys.exit(1)
                update_existing = True
            except omogenjudge.storage.models.Problem.DoesNotExist:
                update_existing = False

            with ProblemVerifier(problem, diagnostics) as verifier:
                result = verifier.check(Context())
            if result.errors:
                logger.error("Problem has errors: exiting")
                sys.exit(1)
            if result.warnings and not options['ignore_warnings']:
                if not ask_yes_or_no("Problem has warnings: continue (y/N)? ", False):
                    sys.exit(1)
            if result.timelim is None:
                logger.error("Could not determine a time limit for the problem: exiting")
                sys.exit(1)
            install_problem(problem, diagnostics, time_limit=result.timelim, update_existing=update_existing)
            logger.info("Problem %s installed", problem.shortname)
