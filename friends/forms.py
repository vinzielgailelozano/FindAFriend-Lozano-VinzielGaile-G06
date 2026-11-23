import re

from django import forms

from accounts.forms import StyledFormMixin
from accounts.models import User

from .models import FriendRequest

LINK_PATTERN = re.compile(r"(https?://|www\.)", re.IGNORECASE)


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


class FriendRequestForm(StyledFormMixin, forms.ModelForm):
    """Used to send a request and to edit the message of a pending one."""

    class Meta:
        model = FriendRequest
        fields = ("message",)
        labels = {"message": "Message (optional)"}
        widgets = {
            "message": forms.Textarea(
                attrs={"rows": 3, "maxlength": 200, "placeholder": "Hi! I'm also in BSIT 2. Want to be study buddies?"}
            )
        }
        help_texts = {"message": "Up to 200 characters. Links aren't allowed."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_message(self):
        message = " ".join(self.cleaned_data.get("message", "").split())
        if LINK_PATTERN.search(message):
            raise forms.ValidationError("For everyone's safety, links aren't allowed in friend request messages.")
        return message
