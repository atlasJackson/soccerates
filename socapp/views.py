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
    # Get the list of fixtures. Ordered the same as answers.
    # Should create a helper function which gets the fixtures corresponding to fixture.STAGE in the future.
    fixtures = group_fixtures_dictionary()
    context_dict['fixtures'] = fixtures

    # Create as many formsets as there are fixtures whose scores are to be predicted.
    AnswerFormSet = formset_factory(AnswerForm, extra=len(fixtures))

    # Check if the request was HTTP POST.
    if request.method == 'POST':
        answer_formset = AnswerFormSet(request.POST)

        # Check if the provided form is valid.
        if answer_formset.is_valid():
            index = 0
            # Get score predictions from corresponding form for each fixture.
            for answer_form in answer_formset:
                a = Answer.objects.create(
                    user=request.user, 
                    fixture=fixtures[index],
                    team1_goals=answer_form.cleaned_data.get('team1_goals'),
                    team2_goals=answer_form.cleaned_data.get('team2_goals')
                )

                index += 1

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
            context_dict['answer_formset'] = AnswerFormSet()
        else:
            context_dict['answer_formset'] = None

    return render(request, 'answer_form.html', context=context_dict)

# Returns a dictionary whose keys are the groups and whose values are a queryset of the fixtures in that group. 
def group_fixtures_dictionary():
    fixtures = {}
    for group in Team.group_names:
        fixtures[group] = Fixture.all_fixtures_by_group(group)

    return fixtures
