"""Feedback on sample test cases that a submission was rejected on.

For rejected sample test cases, the judgehost stores what the submission wrote (see
SubmissionCaseFeedback). Together with the test data, this is shown to the submitter. This is only
ever done for sample test cases, since it reveals the test data.
"""
import codecs
import dataclasses
import re
import signal
from typing import Optional, Union

from django.db import models
from django.db.models.functions import Length, Substr

from omogenjudge.storage.models import Status, StoredFile, SubmissionCaseFeedback, SubmissionRun, Verdict

# Must match the name of the group that the judgehost captures feedback for.
SAMPLE_GROUP_NAME = 'data/sample'

# How much of the input and answer files of a test case to display.
MAX_TESTDATA_BYTES = 64 * 1024

_REPLACEMENT_CHARACTER = '�'
# Control characters that would be invisible or confusing when displayed. Tabs, newlines and
# carriage returns are kept.
_CONTROL_CHARACTERS = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

BytesLike = Union[bytes, bytearray, memoryview]


@dataclasses.dataclass(frozen=True)
class FeedbackText:
    text: str
    # Whether there was more text than what is included.
    truncated: bool = False


@dataclasses.dataclass(frozen=True)
class SampleFeedback:
    testcase_name: str
    verdict: Verdict
    input: FeedbackText
    answer: FeedbackText
    output: FeedbackText
    error: FeedbackText
    message: FeedbackText
    # For run-time errors, exactly one of exit_code and exit_signal is set (if they are known).
    exit_code: Optional[int] = None
    exit_signal: Optional[int] = None
    exit_signal_name: Optional[str] = None


def decode_for_display(data: Optional[BytesLike], truncated: bool = False) -> FeedbackText:
    """Converts arbitrary bytes (such as the output of a submission) to text that is safe to display.

    Invalid UTF-8 and control characters are replaced by the Unicode replacement character.
    """
    raw = bytes(data) if data is not None else b''
    decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
    # If the data was truncated, it may have been cut in the middle of a character. That partial
    # character is then dropped rather than displayed as an invalid one.
    text = decoder.decode(raw, final=not truncated)
    return FeedbackText(text=_CONTROL_CHARACTERS.sub(_REPLACEMENT_CHARACTER, text), truncated=truncated)


def signal_name(signal_number: Optional[int]) -> Optional[str]:
    if signal_number is None:
        return None
    try:
        return signal.Signals(signal_number).name
    except ValueError:
        return None


def _file_previews(file_hashes: set[str], limit: int) -> dict[str, FeedbackText]:
    """Returns the first limit bytes of the given stored files, without loading the entire files."""
    if not file_hashes:
        return {}
    files = (StoredFile.objects
             .filter(file_hash__in=file_hashes)
             .annotate(preview=Substr('file_contents', 1, limit, output_field=models.BinaryField()),
                       size=Length('file_contents'))
             .values_list('file_hash', 'preview', 'size'))
    return {file_hash: decode_for_display(preview, truncated=size > limit) for file_hash, preview, size in files}


def get_sample_feedback(run: SubmissionRun) -> list[SampleFeedback]:
    """Returns feedback for the sample test cases that the run was rejected on, ordered by test case name."""
    # When a run is queued for rejudging, feedback from the previous judging is not yet cleared.
    if run.get_status() not in (Status.RUNNING, Status.DONE):
        return []
    rows = (SubmissionCaseFeedback.objects
            .filter(submission_run=run,
                    # The judgehost only stores feedback for sample cases, but since the test data
                    # is displayed, make sure of it here as well.
                    problem_testcase__problem_testgroup__testgroup_name=SAMPLE_GROUP_NAME,
                    problem_testcase__problem_testgroup__problem_version_id=run.problem_version_id)
            .select_related('problem_testcase')
            .order_by('problem_testcase__testcase_name', 'submission_case_feedback_id'))
    # There should only be one row per test case; if not, the latest one wins.
    by_testcase = {row.problem_testcase_id: row for row in rows}
    if not by_testcase:
        return []

    file_hashes: set[str] = set()
    for row in by_testcase.values():
        file_hashes.add(row.problem_testcase.input_file_id)
        file_hashes.add(row.problem_testcase.output_file_id)
    previews = _file_previews(file_hashes, MAX_TESTDATA_BYTES)
    missing = FeedbackText(text='')

    feedback = []
    for row in by_testcase.values():
        testcase = row.problem_testcase
        feedback.append(SampleFeedback(
            testcase_name=testcase.testcase_name,
            verdict=Verdict(row.verdict),
            input=previews.get(testcase.input_file_id, missing),
            answer=previews.get(testcase.output_file_id, missing),
            output=decode_for_display(row.team_output, row.team_output_truncated),
            error=decode_for_display(row.team_error, row.team_error_truncated),
            message=decode_for_display(row.validator_message),
            exit_code=row.exit_code,
            exit_signal=row.exit_signal,
            exit_signal_name=signal_name(row.exit_signal),
        ))
    return feedback
