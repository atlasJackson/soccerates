from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django import forms

from socapp.models import Answer, Fixture

# For registering new users
class RegistrationForm(forms.ModelForm):
    alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', 'Only alphanumeric characters are allowed.')

    username = forms.CharField(min_length=4, max_length=50, validators=[alphanumeric], widget=forms.TextInput(attrs={'autofocus':'true'}))
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label="Confirm password")

    class Meta:
        model = User
        fields = ('username', 'email', 'password')
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).count() > 0:
            raise ValidationError("Username already exists")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).count() > 0:
            raise ValidationError("Email already exists")
        return email
    
    def clean_password_confirm(self):
        pw1 = self.cleaned_data['password']
        pw2 = self.cleaned_data['password_confirm']

        if pw1 and not pw1 == pw2:
            raise ValidationError("Passwords don't match")
        return pw2


    # Override to hash password by using the User model manager's 'create_user' method
    def save(self, *args, **kwargs):
        user = User.objects.create_user(
            self.cleaned_data['username'],
            self.cleaned_data['email'],
            self.cleaned_data['password']
        )
        return user


class AnswerForm(forms.ModelForm):
    # fixture - hidden field that ties the answer to a fixture
    fixture = forms.ModelChoiceField(queryset=Fixture.objects.all(), widget=forms.HiddenInput())
    team1_goals = forms.IntegerField(min_value=0, max_value=10, widget=forms.NumberInput())
    team2_goals = forms.IntegerField(min_value=0, max_value=10, widget=forms.NumberInput())

    class Meta:
        model = Answer
        fields = ('fixture','team1_goals', 'team2_goals')