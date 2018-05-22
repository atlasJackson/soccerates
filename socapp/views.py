from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic.edit import CreateView

from django.forms import formset_factory
from .forms import RegistrationForm, AnswerForm

from .models import Fixture, Answer, Team


def index(request):
    return render(request, "index.html")

# Display the groups (which should update with the results), along w/ their fixtures. On a separate tab, show post-group matches
def world_cup_schedule(request):
    
    fixtures = group_fixtures_dictionary()

    context = {
        'fixtures': fixtures
    }
    return render(request, "world_cup.html", context)

class RegistrationView(SuccessMessageMixin, CreateView):
    template_name = "register.html"
    form_class = RegistrationForm
    success_url = "/"
    success_message = "Registration successful. Welcome, %(username)s"

    # Override to auto-login user when they register
    def form_valid(self, form):
        valid = super().form_valid(form)
        username = self.request.POST['username']
        pw = self.request.POST['password']
        user = authenticate(username=username, password=pw)
        login(self.request, user)
        return valid


@login_required
def answer_form(request):
    
    context_dict = {}

    # Create as many formsets as there are fixtures whose scores are to be predicted.
    group_fixtures = Fixture.all_fixtures_by_stage(Fixture.GROUP).order_by('team1__group', 'match_date')
    AnswerFormSet = formset_factory(AnswerForm, extra=len(group_fixtures), max_num=len(group_fixtures))
    formset = AnswerFormSet()

    # The zip Python method takes two (or more) lists/iterables, and binds them together in tuples, based on their index in each list (so the lists must have the same len).
    # So we're binding each form in the formset with a fixture, and setting the initial value of the form's hidden Fixture field to the associated/'zipped' fixture.
    # We also create a zipped_groups list, so we can track each fixture/form iteration's group in the template
    zipped_groups = []
    for match, form in zip(group_fixtures, formset):
        form.fields['fixture'].initial = match
        zipped_groups.append(match.team1.group)

    # With the initial values set within the form, we add the zipped fixtures/forms/groups data structure to the template context. 
    # This allows us to iterate over each fixture/form in the template, with access to the associated group, and will ensure they're in sync.
    context_dict['fixtures_and_forms'] = zip(group_fixtures, formset, zipped_groups)

    # Check if the request was HTTP POST.
    if request.method == 'POST':
        answer_formset = AnswerFormSet(request.POST)

        # Check if the provided form is valid.
        if answer_formset.is_valid():
            # Get score predictions from corresponding form for each fixture.
            for answer_form in answer_formset:
                fixt = answer_form.cleaned_data.get('fixture')

                # A check to see if the user has already provided an answer for this fixture.
                # If not, we create the Answer. Otherwise (in the else), we update.
                # In future, we'll need to block this off based on a cutoff date (or just now show the answer form)
                if Answer.objects.filter(user=request.user, fixture=fixt).count() == 0:
                    
                    Answer.objects.create(
                        user=request.user, 
                        fixture=fixt,
                        team1_goals=answer_form.cleaned_data.get('team1_goals'),
                        team2_goals=answer_form.cleaned_data.get('team2_goals')
                    )

                else:
                    Answer.objects.filter(user=request.user,fixture=fixt) \
                        .update(team1_goals=answer_form.cleaned_data.get('team1_goals'),
                                team2_goals=answer_form.cleaned_data.get('team2_goals'))

            # Return to the index for now.
            return HttpResponseRedirect(reverse('index'))
        else:
            # Print problems to the terminal.
            print(answer_formset.errors)
    else:
        # Not an HTTP POST, so we render our forms.
        # These forms will be blank, ready for user input.
        # But first we check if the user has already submitted answers.
        if True: ## Fix this condition
            context_dict['answer_formset'] = formset
        else:
            context_dict['answer_formset'] = None

    return render(request, 'answer_form.html', context_dict)

# Returns a dictionary whose keys are the groups and whose values are a queryset of the fixtures in that group. 
def group_fixtures_dictionary():
    fixtures = {}
    for group in Team.group_names:
        fixtures[group] = Fixture.all_fixtures_by_group(group)

    return fixtures