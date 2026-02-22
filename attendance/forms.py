from django import forms
from .models import Course

class StartSessionForm(forms.Form):
    course_id = forms.ChoiceField(choices=[])
    minutes = forms.IntegerField(min_value=1, max_value=15)
    expected_count = forms.IntegerField(min_value=0, max_value=500, required=False)

    def __init__(self, *args, **kwargs):
        faculty = kwargs.pop("faculty", None)
        super().__init__(*args, **kwargs)
        if faculty:
            courses = Course.objects.filter(faculty=faculty).order_by("code", "section")
            self.fields["course_id"].choices = [(c.id, str(c)) for c in courses]
        else:
            self.fields["course_id"].choices = []


from django import forms

class MarkAttendanceForm(forms.Form):
    otp = forms.CharField(max_length=10)
    selfie_data = forms.CharField(widget=forms.HiddenInput, required=True)