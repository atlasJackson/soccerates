from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Sum
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import CreateView

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.forms import formset_factory
from .forms import RegistrationForm, UserProfileForm, AnswerForm, LeaderboardForm, PrivateAccessForm

from .models import UserProfile, Fixture, Answer, Team, Leaderboard
from . import utils

import datetime

def test(request):

    fixtures = group_fixtures_dictionary()
    fixtures2 = Fixture.objects.order_by('match_date')
    upcoming_fixtures = Fixture.objects.filter(status=Fixture.MATCH_STATUS_NOT_PLAYED).order_by('match_date')[:5]
    past_fixtures = Fixture.objects.filter(status=Fixture.MATCH_STATUS_PLAYED).order_by('-match_date')[:5]

    AnswerFormSet = formset_factory(AnswerForm, extra=len(fixtures), max_num=len(fixtures))
    answer_formset = AnswerFormSet()

    context = {
        'fixtures': fixtures,
        'fixtures2': fixtures2,
        'upcoming_fixtures' : upcoming_fixtures,
        'past_fixtures': past_fixtures,
        'answer_formset': answer_formset,
    }

    if request.method == 'POST':
        answer_formset = AnswerFormSet(request.POST)

    return render(request, "test.html", context)





def index(request):

    fixtures = group_fixtures_dictionary()
    upcoming_fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_NOT_PLAYED).order_by('match_date')[:5]
    past_fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_PLAYED).order_by('-match_date')[:5]

    context = {
        'fixtures': fixtures,
        'upcoming_fixtures' : upcoming_fixtures,
        'past_fixtures': past_fixtures,
    }

    try:
        ranking = utils.get_user_ranking(request.user)
        usercount = get_user_model().objects.count()
        points_percentage = utils.points_per_fixture(request.user)

        context['ranking'] = ranking
        context['usercount'] = usercount
        context['points_percentage'] = points_percentage
    
    except AttributeError:
        pass



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

    # Code taken from https://simpleisbetterthancomplex.com/tutorial/2016/08/03/how-to-paginate-with-django.html
    page = request.GET.get('page', 1)

    paginator = Paginator(answers, 12)
    try:
        answers_subset = paginator.page(page)
    except PageNotAnInteger:
        answers_subset = paginator.page(1)
    except EmptyPage:
        answers_subset = paginator.page(paginator.num_pages)

    ranking = utils.get_user_ranking(request.user)
    usercount = get_user_model().objects.count()
    points_percentage = utils.points_per_fixture(request.user)
    public_lb = Leaderboard.objects.filter(users=request.user.pk, is_private=False)
    private_lb = Leaderboard.objects.filter(users=request.user.pk, is_private=True)

    context = {
        'answers': answers_subset,
        'ranking': ranking,
        'usercount': usercount,
        'public_lb': public_lb,
        'private_lb': private_lb,
        'points_percentage': points_percentage,
    }

    userprofile = UserProfile.objects.get_or_create(user=request.user)[0]
    profile_form = UserProfileForm({'picture': userprofile.picture})
    context ['profile_form'] = profile_form

    # Handle submission of new profile picture.
    # Check if the request was HTTP POST.
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)

        # Check if the provided form is valid.
        if profile_form.is_valid():
            profile_form.save(commit=True)
            return HttpResponseRedirect(reverse("profile"))

        else:
            print (profile_form.errors)

    return render(request, "user_profile.html", context)


@login_required
def answer_form(request):

    context_dict = {'groups': ["A", "B", "C", "D", "E", "F", "G", "H"]}

    # Create as many formsets as there are fixtures whose scores are to be predicted.
    group_fixtures = Fixture.all_fixtures_by_stage(Fixture.GROUP).order_by('team1__group', 'match_date')
    AnswerFormSet = formset_factory(AnswerForm, extra=len(group_fixtures), max_num=len(group_fixtures))
    initial_data = get_initial_data(group_fixtures, request.user)
    
    # Check if the request was HTTP POST.
    if request.method == 'POST':
        answer_formset = AnswerFormSet(request.POST, initial=[data for data in initial_data])
        if answer_formset.is_valid():
            # Get score predictions from corresponding form for each fixture.
            for answer_form in answer_formset:

                # Only process/save the form if the form differs from its initial data. Formsets have a has_changed method for detecting this.
                if answer_form.has_changed():
                    fixt = answer_form.cleaned_data.get('fixture')

                    # Check if the answer can be edited.
                    if not can_edit_answer(fixt):
                        continue

                    # Check to see if the user has already provided an answer for this fixture. If not, create the Answer. Otherwise update.
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
            return HttpResponseRedirect(reverse('profile'))
        else:
            # Print problems to the terminal.
            print(answer_formset.errors)
    else:
        
        # Check user is logged in, otherwise can't render the formset.
        if not request.user.is_anonymous:
            # Not a POST, so all forms will be blank unless the user has already submitted an answer.
            # If answers exist, populate the form with the existing answers.

            zipped_groups = [fixture.team1.group for fixture in group_fixtures]
            formset = AnswerFormSet(initial=[data for data in initial_data])
            management_form = formset.management_form

            # With the initial values set within the form, we add the zipped fixtures/forms/groups data structure to the template context. 
            # This allows us to iterate over each fixture/form in the template, with access to the associated group, and will ensure they're in sync.
            context_dict['fixtures_and_forms'] = zip(group_fixtures, formset, zipped_groups)
            context_dict['management_form'] = management_form

    return render(request, 'answer_form.html', context_dict)


# Determines initial data for an AnswerForm based on the fixtures and user passed in.
# Returns list comprised of dictionaries with the initial data.
def get_initial_data(fixtures, user):
    initial_list = []
    for fixture in fixtures:
        this_initial = {}
        this_initial['fixture'] = fixture.id
        try:
            ans = Answer.objects.get(fixture=fixture, user=user) # Check if user has an answer for this fixture

            this_initial['team1_goals'] = ans.team1_goals
            this_initial['team2_goals'] = ans.team2_goals
        except Answer.DoesNotExist:
            continue
        finally:
            initial_list.append(this_initial)
    return initial_list

# Determines whether a fixture can edited (it can be edited up to 15 mins before its kickoff)
# This returns true or false based on the fixture passed in.
def can_edit_answer(fixture):
    cutoff_time = fixture.match_date - datetime.timedelta(minutes=15)
    return timezone.now() < cutoff_time

    
###############################################
# LEADERBOARD VIEWS
###############################################

@login_required
def leaderboards(request):

    user_leaderboard_set = set(request.user.leaderboard_set.values_list('name',flat=True))
    all_lb = Leaderboard.objects.all().order_by(Lower('name'))

    public_lb = Leaderboard.objects.prefetch_related('users').filter(users=request.user, is_private=False)
    private_lb = Leaderboard.objects.prefetch_related('users').filter(users=request.user, is_private=True)

    # Code taken from https://simpleisbetterthancomplex.com/tutorial/2016/08/03/how-to-paginate-with-django.html
    page = request.GET.get('page', 1)

    paginator = Paginator(all_lb, 5)
    try:
        all_lb_subset = paginator.page(page)
    except PageNotAnInteger:
        all_lb_subset = paginator.page(1)
    except EmptyPage:
        all_lb_subset = paginator.page(paginator.num_pages)

    context_dict = {
        'all_lb_subset': all_lb_subset, 
        'public_lb': public_lb, 
        'private_lb': private_lb,
        'user_leaderboard_set': user_leaderboard_set,
        }

    # If there are errors, do not reinitialise the form.
    leaderboard_form = LeaderboardForm(request.POST or None)
    context_dict['leaderboard_form'] = leaderboard_form

    # Check if the request was HTTP POST.
    if request.method == 'POST':

        context_dict['leaderboard_post'] = True

        # Check if the provided form is valid.
        if leaderboard_form.is_valid():

            # Save the new leaderboard to the database, and add the current user as a member.
            leaderboard = leaderboard_form.save()
            leaderboard.users.add(request.user)
            leaderboard.save()
 
            # Display newly-created leaderboard.
            return HttpResponseRedirect(reverse('show_leaderboard', kwargs={'leaderboard':leaderboard.slug}))

    return render(request, 'leaderboards.html', context_dict)

##### Leaderboard AJAX views ######
@login_required
@csrf_exempt
def paginate_leaderboards(request):
    if request.is_ajax():
        page = request.POST.get('page', 1)
        search_term = request.POST.get('search_term', None)

        if search_term == '' or search_term is None:
            all_lb = Leaderboard.objects.all().order_by(Lower('name'))
        else:
            all_lb = Leaderboard.objects.filter(name__contains=search_term).order_by(Lower('name'))

        paginator = Paginator(all_lb, 5)
        try:
            all_lb_subset = paginator.page(page)
        except PageNotAnInteger:
            all_lb_subset = paginator.page(1)
        except EmptyPage:
            all_lb_subset = paginator.page(paginator.num_pages)

        user_leaderboard_set = set(request.user.leaderboard_set.values_list('name',flat=True))        
        context_dict = { 
            'leaderboards': all_lb_subset, 
            'all_boards': True,
            'user_leaderboard_set': user_leaderboard_set,
        }
        return render(request, 'include_leaderboards.html', context_dict)

@login_required
@csrf_exempt
def search_leaderboards(request):
    if request.is_ajax():
        search_term = request.POST.get('search_term', None)
        page = request.POST.get('page', 1)

        # Filter leaderboards by the search term
        if search_term == '' or search_term is None:
            matched_lbs = Leaderboard.objects.order_by(Lower("name"))
        else:
            matched_lbs = Leaderboard.objects.filter(name__contains=search_term).order_by(Lower("name"))
        paginator = Paginator(matched_lbs, 5)
        try:
            matched_lb_subset = paginator.page(page)
        except PageNotAnInteger:
            matched_lb_subset = paginator.page(1)
        except EmptyPage:
            matched_lb_subset = paginator.page(paginator.num_pages)

        user_leaderboard_set = set(request.user.leaderboard_set.values_list('name',flat=True))
        
        context_dict = { 
            'leaderboards': matched_lb_subset, 
            'all_boards': True,
            'user_leaderboard_set': user_leaderboard_set,
        }
        return render(request, 'include_leaderboards.html', context_dict)


@login_required
def show_leaderboard(request, leaderboard):

    try:
        # Get leaderboard with given slug.
        leaderboard = Leaderboard.objects.prefetch_related('users', 'users__profile').get(slug=leaderboard)
        print (request.user in leaderboard.users.all())

        # If there are errors, do not reinitialise the form.
        access_form = PrivateAccessForm(request.POST or None)
        context_dict = {'access_form': access_form, 'leaderboard': leaderboard}

        # Check if the request was HTTP POST.
        if request.method == 'POST':

            # Check if the provided form is valid.
            if access_form.is_valid():

                given_password = access_form.cleaned_data['password']
                hashed_password = make_password(given_password)

                if check_password(given_password, leaderboard.password):
                    leaderboard.users.add(request.user)
                    leaderboard.save()
                    return HttpResponseRedirect(reverse('show_leaderboard', kwargs={'leaderboard':leaderboard.slug}))
     

        if leaderboard.is_private and not request.user in leaderboard.users.all():
            return render(request, 'private_leaderboard_login.html', context_dict)

        # Get a list of all users who are members of the leaderboard.
        members = leaderboard.users.select_related('profile').order_by('-profile__points')
        # Get a collection of board statistics.
        total_points = members.aggregate(tp=Sum('profile__points'))['tp']
        if members:
            average_points = total_points/(members.count())
            percent_above_average = members.filter(profile__points__gte=average_points).count()*100/(members.count())
        else:
            average_points = 0
            percent_above_average = 0

        # Add entities to the context dictionary
        context_dict = {
            'access_form': access_form,
            'leaderboard':leaderboard, 
            'members':members, 
            'total_points': total_points,
            'average_points': average_points,
            'percent_above_average': percent_above_average,
        }

    except Leaderboard.DoesNotExist:
        # We get here if we couldn't find the specified game
        messages.error(request, "No leaderboard with name \'{}\' could be found".format(leaderboard))
        return HttpResponseRedirect(reverse('leaderboards'))

    return render(request, 'show_leaderboard.html', context_dict)


@login_required
def join_leaderboard(request, leaderboard):

    leaderboard = Leaderboard.objects.get(slug=leaderboard)
    user = request.user

    # If board is full, prevent user from joining.
    if leaderboard.users.count() == leaderboard.capacity:
        user_added = False
        board_full = True

    else:    
        leaderboard.users.add(user)
        leaderboard.save()
        user_added = True
        board_full = False

    data = {'user_added': user_added, 'board_full': board_full}

    return JsonResponse(data)


@login_required
def leave_leaderboard(request, leaderboard):

    leaderboard = Leaderboard.objects.get(slug=leaderboard)
    board_empty = False
    
    user = request.user

    leaderboard.users.remove(user)
    leaderboard.save()
    user_removed = True
    left_private_board = False

    if leaderboard.is_private:
        left_private_board = True

    if leaderboard.users.count() == 0:
        board_empty = True
        leaderboard.delete()

    data = {
        'user_removed': user_removed, 
        'board_empty': board_empty, 
        'left_private_board': left_private_board,
        'url': reverse('leaderboards')
    }

    return JsonResponse(data)


###############################################
# FORUMS VIEWS
###############################################

def forums(request):

    context_dict = {}
    return render(request, 'forums.html', context_dict)


#################
## AUTH VIEWS
#################

class RegistrationView(SuccessMessageMixin, CreateView):
    template_name = "register.html"
    form_class = RegistrationForm
    success_url = "profile"
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
    f = Fixture.objects.select_related('team1', 'team2').filter(stage=Fixture.GROUP).order_by('team1__group', 'match_date')
    for group in Team.group_names:
        fixtures[group] = f.filter(team1__group=group)

    return fixtures