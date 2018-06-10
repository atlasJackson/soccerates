from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from django import forms

from socapp.models import UserProfile, Answer, Fixture, Leaderboard

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

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('picture',)


class AnswerForm(forms.ModelForm):
    # fixture - hidden field that ties the answer to a fixture
    fixture = forms.ModelChoiceField(queryset=Fixture.objects.all(), widget=forms.HiddenInput())
    team1_goals = forms.IntegerField(min_value=0, max_value=10, widget=forms.NumberInput(), required=False)
    team2_goals = forms.IntegerField(min_value=0, max_value=10, widget=forms.NumberInput(), required=False)

    class Meta:
        model = Answer
        fields = ('fixture', 'team1_goals', 'team2_goals')


class LeaderboardForm(forms.ModelForm):

    name = forms.CharField(max_length=128, label="Name")
    capacity = forms.IntegerField(min_value=2, max_value=100, widget=forms.NumberInput(), label="Capacity (2-100):")
    is_private = forms.BooleanField(widget=forms.CheckboxInput(), initial=False, required=False, \
                                    label="Set to Private? (Requires password to join)")
    password = forms.CharField(widget=forms.PasswordInput(), label="Password", required=False)
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label="Confirm password", required=False)

    class Meta:
        model = Leaderboard
        fields = ('name', 'capacity', 'is_private', 'password', 'password_confirm')

    def clean_password(self):
        password = self.cleaned_data.get('password')
        print (password)
        private = self.cleaned_data['is_private']

        if private and not password:
            raise ValidationError("Private leaderboards require a password.")
        return password

    def clean_password_confirm(self):
        pw1 = self.cleaned_data.get('password')
        pw2 = self.cleaned_data.get('password_confirm')

        if pw1 and not pw1 == pw2:
            raise ValidationError("Passwords don't match")
        return pw2

    def save(self, *args, **kwargs):
        private = self.cleaned_data['is_private']

        leaderboard = Leaderboard.objects.create(
            name=self.cleaned_data['name'],
            capacity=self.cleaned_data['capacity'],
            is_private=private,
        )

        if self.cleaned_data['is_private']:

            password = make_password(self.cleaned_data['password'])
            leaderboard.password = password
            leaderboard.save()
    
        return leaderboard


class PrivateAccessForm(forms.Form):

    password = forms.CharField(widget=forms.PasswordInput(), label="Password", required=True)

    class Meta:
        fields = ('password',)
