from django import forms

from accounts.forms import StyledFormMixin
from accounts.models import User


class StudentSearchForm(StyledFormMixin, forms.Form):
    """Filters on the Find Friends page (GET form, every field optional)."""

    q = forms.CharField(required=False, max_length=100, label="Search")
    course = forms.CharField(required=False, max_length=100)
    year_level = forms.TypedChoiceField(
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Any year")] + list(User.YearLevel.choices),
    )
    student_status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[("", "Any status")] + list(User.StudentStatus.choices),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["q"].widget.attrs["placeholder"] = "Name, username or interest (e.g. badminton)"
        self.fields["course"].widget.attrs["placeholder"] = "Course, e.g. BSIT"
        self._style_fields()
