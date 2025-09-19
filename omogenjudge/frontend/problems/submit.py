import django.forms as forms
from crispy_forms.bootstrap import FieldWithButtons
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from django.core.exceptions import PermissionDenied
from django.core.files.uploadhandler import FileUploadHandler, StopUpload
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from omogenjudge.frontend.decorators import requires_contest, requires_user
from omogenjudge.problems.lookup import problem_by_name
from omogenjudge.problems.permissions import can_submit_in_contest, can_view_problem
from omogenjudge.storage.models import Account, Contest, Problem
from omogenjudge.storage.models.langauges import Language
from omogenjudge.submissions.create import create_submission
from omogenjudge.util.contest_urls import reverse_contest
from omogenjudge.util.django_types import OmogenRequest
from omogenjudge.storage.models import Language

SOURCE_CODE_LIMIT = 200000

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class SubmitForm(forms.Form):
    upload_files = MultipleFileField(
        label="",
        widget=MultipleFileInput(attrs={'class': 'form-control'}))
    language = forms.ChoiceField(
        label="",
        choices=[],  # Empty choices initially
        widget=forms.Select(attrs={'class': 'form-select'}))


    def __init__(self, problem_short_name: str, allowed_languages=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs['id'] = 'submit'
        self.helper.layout = Layout(
            'upload_files',
            FieldWithButtons(
                'language',
                Submit('submit', 'Submit'),
            )
        )
        self.helper.form_action = reverse_contest('submit', short_name=problem_short_name)

        self.fields['language'].choices = list(filter(lambda lang: allowed_languages is None or lang[1] in allowed_languages, Language.as_choices()))


class SourceLimitCappingHandler(FileUploadHandler):
    def receive_data_chunk(self, raw_data, start):
        if start + len(raw_data) > self.remaining:
            self.request.META['upload_was_capped'] = True
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        self.remaining -= file_size
        return None

    def __init__(self, request, size_limit, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.remaining = size_limit

def language_allowed(request: OmogenRequest, language):
    contest = request.contest
    if not contest:
        return True
    if contest.allow_only_python:
        return language==Language.PYTHON3
    return True

@csrf_exempt
@requires_user()
@requires_contest
def submit(request: OmogenRequest, short_name: str, user: Account, contest: Contest) -> HttpResponse:
    try:
        problem = problem_by_name(short_name)
    except Problem.DoesNotExist:
        raise Http404()
    if not can_view_problem(problem):
        raise Http404()
    if not can_submit_in_contest(contest):
        raise PermissionDenied()
    size_limit = min(SOURCE_CODE_LIMIT,problem.submission_size_limit_in_bytes)
    request.upload_handlers.insert(0, SourceLimitCappingHandler(request, size_limit))  # type: ignore
    form = SubmitForm(problem.short_name, data=request.POST, files=request.FILES)
    exceeded_file_size = request.META.get('upload_was_capped', False)
    if exceeded_file_size:
        return JsonResponse({'errors': {'upload_files': [f'The source code limit is {size_limit // 1000} KB.']}})

    # Note: don't validate the rest of the form if we killed uploads
    if not form.is_valid():
        return JsonResponse({'errors': form.errors})
    language = Language(form.cleaned_data['language'])
    if not language_allowed(request, language):
        return JsonResponse({'errors': {'upload_files': [f'Only python is allowed.']}})
    submission = create_submission(
        owner=user,
        problem=problem,
        language=language,
        files={f.name: f.read() for f in form.cleaned_data["upload_files"] if f.name is not None}
    )
    return JsonResponse({'submission_link': reverse_contest('submission', sub_id=submission.submission_id)})
