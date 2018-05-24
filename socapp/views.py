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
    upcoming_fixtures = Fixture.objects.filter(status=Fixture.MATCH_STATUS_NOT_PLAYED).order_by('match_date')[:5]
    past_fixtures = Fixture.objects.filter(status=Fixture.MATCH_STATUS_PLAYED).order_by('-match_date')[:5]

    context = {
        'upcoming_fixtures' : upcoming_fixtures,
        'past_fixtures': past_fixtures,
    }

    return render(request, "index.html", context)

# Display the groups (which should update with the results), along w/ their fixtures. On a separate tab, show post-group matches
def world_cup_schedule(request):
    
    fixtures = group_fixtures_dictionary()

    context = {
        'fixtures': fixtures
    }
    return render(request, "world_cup.html", context)

@login_required
def user_profile(request):
    answers = request.user.profile.get_predictions()
    
    context = {
        'answers': answers
    }
    return render(request, "user_profile.html", context)

@login_required
def answer_form(request):
    
    context_dict = {}

    # Create as many formsets as there are fixtures whose scores are to be predicted.
    group_fixtures = Fixture.all_fixtures_by_stage(Fixture.GROUP).order_by('team1__group', 'match_date')
    AnswerFormSet = formset_factory(AnswerForm, extra=len(group_fixtures), max_num=len(group_fixtures))

    # Check if the request was HTTP POST.
    if request.method == 'POST':
        answer_formset = AnswerFormSet(request.POST, initial=[{'fixture': f.id} for f in group_fixtures])

        # Check if the provided form is valid.
        if answer_formset.is_valid():
            # Get score predictions from corresponding form for each fixture.
            for answer_form in answer_formset:

                # Only process/save the form if the form differs from its initial data. Formsets have a has_changed method for detecting this.
                if answer_form.has_changed():
                    fixt = answer_form.cleaned_data.get('fixture')
                    # A check to see if the user has already provided an answer for this fixture.
                    # If not, we create the Answer. Otherwise (in the else), we update.
                    # In future, we'll need to block this off based on a cutoff date (or just not show the answer form)
                    if not Answer.objects.filter(user=request.user, fixture=fixt).exists():
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
        # These forms will be blank, ready for user input, unless the user has already submitted an answer.
        # But first we check if the user has already submitted answers. If so, we populate the form with the existing answers.

        user_answers = []
        for fixture in group_fixtures:
            ans = Answer.objects.select_related('fixture','user') \
                .filter(fixture=fixture, user=request.user) # Check if user has an answer for this fixture
            if ans.count() > 0:
                user_answers.append(ans[0]) # If so add it to the answers list
            else:
                user_answers.append(None) # If not, append None to the array so we can ignore it in the listcomp below when setting initial values
        
        # Set the formset, w/ initial values if an answer exists from the user for the fixture in question
        formset = AnswerFormSet(initial=[{'team1_goals': a.team1_goals, "team2_goals": a.team2_goals} for a in user_answers if a is not None])
        management_form = formset.management_form

        # The zip Python method takes two (or more) lists/iterables, and binds them together in tuples, based on their index in each list (so the lists should have the same len).
        # So we're binding each form in the formset with a fixture, and setting the initial value of the form's hidden Fixture field to the associated/'zipped' fixture.
        # We also create a zipped_groups list, so we can track each fixture/form iteration's group in the template
        zipped_groups = []
        for match, form in zip(group_fixtures, formset):
            form.fields['fixture'].initial = match
            zipped_groups.append(match.team1.group)

        # With the initial values set within the form, we add the zipped fixtures/forms/groups data structure to the template context. 
        # This allows us to iterate over each fixture/form in the template, with access to the associated group, and will ensure they're in sync.
        context_dict['fixtures_and_forms'] = zip(group_fixtures, formset, zipped_groups)
        context_dict['management_form'] = management_form

    return render(request, 'answer_form.html', context_dict)



###############################
### USER POINTS CALCULATION
###############################

# Calculates the user's points for games that have already been played, but ahve not yet been added to the user's points total.
def calculate_user_points(user):
    
    # Get completed fixtures.
    fixtures = Fixture.all_completed_fixtures()
    
    for fixture in fixtures:
        # Get user's answer for each completed fixture. If no answer exists then continue to the next fixture.
        try:
            ans = Answer.objects.select_related('fixture','user') \
                    .filter(fixture=fixture, user=user)[0] 

        except Answer.DoesNotExist:
            continue

        # Skip fixture if points have been added.
        if (ans.POINTS_ADDED):
            continue

        # Get actual and predicted goals scored for each team in the fixture
        user_team1_goals = ans.team1_goals
        user_team2_goals = ans.team2_goals
        actual_team1_goals = fixture.team1_goals
        actual_team2_goals = fixture.team2_goals

        # First check if result is correct, i.e. prediction of goals scored for each time match.
        team1_accuracy = user_team1_goals - actual_team1_goals
        team2_accuracy = user_team2_goals - actual_team2_goals

        if (team1_accuracy == team2_accuracy == 0):
            add_user_points(user, ans, 5)

        # If not, then check for other conditions to get points. 
        else:

            # Get actual/predicted total goals, and actual/predicted goal difference.
            user_total_goals = user_team1_goals + user_team2_goals
            actual_total_goals = actual_team1_goals + actual_team2_goals
            user_goal_difference = user_team1_goals - user_team2_goals
            actual_goal_difference = actual_team1_goals - actual_team2_goals

            # Check the result is correct
            if ((user_goal_difference > 0 and actual_goal_difference > 0) or
                (user_goal_difference < 0 and actual_goal_difference < 0) or
                (user_goal_difference == actual_goal_difference == 0)): 
                
                add_user_points(user, ans, 2)

            # Check the total goals scored or the goal difference is correct (can't have both, or the prediction would be correct).
            elif ((user_total_goals == actual_total_goals) or (user_goal_difference == actual_goal_difference)):
                add_user_points(user, ans, 1)


# Helper method to add to user's total points.
def add_user_points(user, answer, pts):

    # Add points to user's total.
    user.points += pts
    user.save()
    
    # Update answer entry so points for this fixture aren't given to the user in the future.
    answer.points_added = answer.POINTS_ADDED
    answer.save()


#################
## AUTH VIEWS
#################

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


#################################
### HELPER METHODS
#################################

# Returns a dictionary whose keys are the groups and whose values are a queryset of the fixtures in that group. 
def group_fixtures_dictionary():
    fixtures = {}
    for group in Team.group_names:
        fixtures[group] = Fixture.all_fixtures_by_group(group)

    return fixtures