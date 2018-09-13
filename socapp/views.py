from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.db.models import F, Sum
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.forms import formset_factory
from .forms import UserProfileForm, AnswerForm, LeaderboardForm, PrivateAccessForm

from .models import Fixture, Answer, Team, Leaderboard, Tournament
from socapp_auth.models import UserProfile
from . import utils

import datetime, re

def test(request):
    #return render(request, "test.html", context)
    return HttpResponseRedirect(reverse("index"))

def index(request):

    # Get current/previous tournaments
    upcoming_tournaments = Tournament.objects.filter(start_date__gt=timezone.now()).order_by('start_date')
    past_tournaments = Tournament.objects.exclude(start_date__gt=timezone.now())

    group_fixtures = group_fixtures_dictionary()
    group_fixtures_exist = any(group_fixtures.values())

    ### Convert below to tournament specific ###
    ro16_fixtures = Fixture.all_fixtures_by_stage(Fixture.ROUND_OF_16).order_by('match_date')
    qf_fixtures = Fixture.all_fixtures_by_stage(Fixture.QUARTER_FINALS).order_by('match_date')
    sf_fixtures = Fixture.all_fixtures_by_stage(Fixture.SEMI_FINALS).order_by('match_date')
    tpp_fixture = Fixture.all_fixtures_by_stage(Fixture.TPP).order_by('match_date')
    final_fixture = Fixture.all_fixtures_by_stage(Fixture.FINAL).order_by('match_date')

    upcoming_fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_NOT_PLAYED).order_by('match_date')[:5]
    
    past_fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_PLAYED).order_by('-match_date')[:5]

    if upcoming_fixtures.exists():
        is_international = upcoming_fixtures[0].tournament.is_international
    elif past_fixtures.exists():
        is_international = past_fixtures[0].tournament.is_international

    context = {
        'group_fixtures_exist': group_fixtures_exist,
        'group_fixtures': group_fixtures,
        'ro16_fixtures' : ro16_fixtures,
        'qf_fixtures' : qf_fixtures,
        'sf_fixtures': sf_fixtures,
        'tpp_fixture' : tpp_fixture,
        'final_fixture' : final_fixture,
        'upcoming_fixtures' : upcoming_fixtures,
        'past_fixtures': past_fixtures,
        'is_international': is_international,
        'upcoming_tournaments': upcoming_tournaments,
        'past_tournaments': past_tournaments
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
def tournaments(request):
    
    group_fixtures = group_fixtures_dictionary()
    group_fixtures_exist = any(group_fixtures.values())

    context = {
        'fixtures': group_fixtures,
        'group_fixtures_exist': group_fixtures_exist
    }
    return render(request, "world_cup.html", context)


@login_required
@csrf_exempt
def user_profile(request, username=None):

    try:
        user = get_user_model().objects.get(username=username)
    except:
        if username is None:
            user = request.user
        else:
            return HttpResponseRedirect(reverse("index"))

    # If not the user's profile, use this to determine if they are on the friends list. 
    is_friend = False

    answers = user.profile.get_predictions()
    group_answers = answers.filter(fixture__stage=Fixture.GROUP).order_by("fixture__team1__group", "fixture__match_date")
    knockout_answers = answers.exclude(fixture__stage=Fixture.GROUP)
    # Filter out fixtures not yet played if viewing someone else's profile.
    if user.username != request.user.username:
        group_answers = [a for a in group_answers if a.points_added]
        knockout_answers = [a for a in knockout_answers if a.points_added]
        if user in request.user.profile.friends.all():
            is_friend = True

    if request.is_ajax():
        page = request.POST.get('page', 1)
        group_answers_subset = paginated_data(group_answers, num_per_page=12, page=page)

        data = {
            'page_html': render_to_string('ajax_partials/group_predictions.html', {'group_answers': group_answers_subset })
        }
        return JsonResponse(data)
    else:
        group_answers_subset = paginated_data(group_answers, num_per_page=12, page=1)
    
    ranking = utils.get_user_ranking(user)
    franking = utils.get_user_franking(user)
    usercount = get_user_model().objects.count()
    points_percentage = utils.points_per_fixture(user)
    public_lb = Leaderboard.objects.filter(users=user.pk, is_private=False)
    private_lb = Leaderboard.objects.filter(users=user.pk, is_private=True)

    context = {
        'user': user,
        'is_friend': is_friend,
        'group_answers': group_answers_subset,
        'knockout_answers': knockout_answers,
        'ranking': ranking,
        'franking': franking,
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
def add_friend(request, username):

    # Get user and friend User objects.
    user = request.user
    friend = get_user_model().objects.get(username=username)

    # Variable to check success.
    friend_added = False

    # Prevent action if user and friend are the same person (can't add ourself to friends list).
    if user != friend:
        user.profile.friends.add(friend)
        user.save()
        friend_added = True

    data = {'friend_added': friend_added}

    return JsonResponse(data)

@login_required
def remove_friend(request, username):

    # Get user and friend User objects.
    user = request.user
    friend = get_user_model().objects.get(username=username)

    # Variable to check success.
    friend_removed = False

    # Prevent action if user and friend are the same person (can't add ourself to friends list).
    if user != friend:
        user.profile.friends.remove(friend)
        user.save()
        friend_removed = True

    data = {'friend_removed': friend_removed, "is_friend": False}

    return JsonResponse(data)


# Takes data, a number of entries to display per-page, and the page to display.
# Returns the relevant page for the data set.
def paginated_data(data, num_per_page, page=1):
    paginator = Paginator(data, num_per_page)
    try:
        data_subset = paginator.page(page)
    except PageNotAnInteger:
        data_subset = paginator.page(1)
    except EmptyPage:
        data_subset = paginator.page(paginator.num_pages)
    return data_subset


@login_required
def points_system(request):
    return render(request, 'points_system.html', {})

@login_required
def answer_form(request):
    return render(request, 'answer_form.html', {})

@login_required
def answer_form_selected(request, stage):

    # Check if the group stage has been selected to handle the required group-specific logic in this view, and the template.
    stage_is_group = (stage == "group_stage")
    context_dict = {
        'groups': ["A", "B", "C", "D", "E", "F", "G", "H"], 
        'stage_is_group': stage_is_group,
        'stage': stage, 
    }

    # Forms for the group stage.
    if stage_is_group:
        group_fixtures = Fixture.all_fixtures_by_stage(Fixture.GROUP).order_by('team1__group', 'match_date')
        AnswerFormSet = formset_factory(AnswerForm, extra=len(group_fixtures), max_num=len(group_fixtures))
        initial_data = get_initial_data(group_fixtures, request.user)    
    # Forms for the knockout stage.
    else:
        knockout_fixtures = get_form_fixtures(stage)
        context_dict['knockout_fixtures'] = knockout_fixtures
        AnswerFormSet = formset_factory(AnswerForm, extra=len(knockout_fixtures), max_num=len(knockout_fixtures))
        initial_data = get_initial_data(knockout_fixtures, request.user, True) # Boolean argument adds ET/Penalties to initial data.

   
    # If POST, check formset is valid, and if so process the formset and redirect to profile page on completion.
    if request.method == 'POST':
        answer_formset = AnswerFormSet(request.POST, initial=[data for data in initial_data])
        if answer_formset.is_valid():
            process_formset(answer_formset, request.user)
            return HttpResponseRedirect(reverse('profile'))
        else:
            # Print problems to the terminal.
            print(answer_formset.errors)
    else:
        if stage_is_group:
            # Not a POST, so all forms will be blank unless the user has already submitted an answer.
            # If answers exist, populate the form with the existing answers.
            if len(group_fixtures) > 0:
                is_international = group_fixtures[0].tournament.is_international
            else:
                is_international = False # Dummy value for now
                 
            zipped_groups = [fixture.team1.group for fixture in group_fixtures]
            formset = AnswerFormSet(initial=[data for data in initial_data])
            management_form = formset.management_form
            context_dict['fixtures_and_forms'] = zip(group_fixtures, formset, zipped_groups)
            context_dict['management_form'] = management_form
        else:
            if len(knockout_fixtures) > 0:
                is_international = knockout_fixtures[0].tournament.is_international
            else:
                is_international = False
                
            formset = AnswerFormSet(initial=[data for data in initial_data])
            management_form = formset.management_form

            context_dict['fixtures_and_forms'] = zip(knockout_fixtures, formset)
            context_dict['management_form'] = management_form

        context_dict['is_international'] = is_international

    return render(request, 'answer_form_selected.html', context_dict)

# Processes a submitted formset of answers
def process_formset(answer_formset, user):

    for answer_form in answer_formset:
        # Only process/save the form if the form differs from its initial data. Formsets have a has_changed method for detecting this.
        if answer_form.has_changed():
            fixt = answer_form.cleaned_data.get('fixture')

            # Check if the answer can be edited.
            if not can_edit_answer(fixt):
                continue

            # Check to see if the user has already provided an answer for this fixture. If not, create the Answer. Otherwise update.
            if not Answer.objects.filter(user=user, fixture=fixt).exists():

                answer = Answer.objects.create(
                    user=user, 
                    fixture=fixt,
                    team1_goals=answer_form.cleaned_data.get('team1_goals'),
                    team2_goals=answer_form.cleaned_data.get('team2_goals'),
                    has_extra_time=answer_form.cleaned_data.get('has_extra_time'),
                    has_penalties=answer_form.cleaned_data.get('has_penalties')
                )

                if answer.has_penalties:
                    answer.has_extra_time = True
                    answer.save()

            else:                    
                answer = Answer.objects.filter(user=user,fixture=fixt)
                answer.update(team1_goals=answer_form.cleaned_data.get('team1_goals'),
                            team2_goals=answer_form.cleaned_data.get('team2_goals'),
                            has_extra_time=answer_form.cleaned_data.get('has_extra_time'),
                            has_penalties=answer_form.cleaned_data.get('has_penalties'))

                if answer[0].has_penalties:
                    answer.update(has_extra_time=True)


# Gets the fixtures to display on the form, based on the stage passed in.
def get_form_fixtures(stage=None):
    if (stage == "round_of_16"):
        return Fixture.all_fixtures_by_stage(Fixture.ROUND_OF_16).order_by('match_date')
    if (stage == "quarter-finals"):
        return Fixture.all_fixtures_by_stage(Fixture.QUARTER_FINALS).order_by('match_date')
    if (stage == "semi-finals"):
        return Fixture.all_fixtures_by_stage(Fixture.SEMI_FINALS).order_by('match_date')
    if (stage == "third_place_play-off"):
        return Fixture.all_fixtures_by_stage(Fixture.TPP)
    if (stage == "final"):
        return Fixture.all_fixtures_by_stage(Fixture.FINAL)

# Determines initial data for an AnswerForm based on the fixtures and user passed in.
# Returns list comprised of dictionaries with the initial data.
def get_initial_data(fixtures, user, knockout=False):
    initial_list = []
    for fixture in fixtures:
        this_initial = {}
        this_initial['fixture'] = fixture.id
        try:
            ans = Answer.objects.get(fixture=fixture, user=user) # Check if user has an answer for this fixture

            this_initial['team1_goals'] = ans.team1_goals
            this_initial['team2_goals'] = ans.team2_goals

            if knockout:
                this_initial['has_extra_time'] = ans.has_extra_time
                this_initial['has_penalties'] = ans.has_penalties

        except Answer.DoesNotExist:
            continue
        finally:
            initial_list.append(this_initial)
    return initial_list

# Determines whether a fixture can edited (it can be edited up to 15 mins before its kickoff)
# This returns true or false based on the fixture passed in.
def can_edit_answer(fixture):
    cutoff_time = fixture.match_date - datetime.timedelta(minutes=75)
    return timezone.now() < cutoff_time

    
###############################################
# LEADERBOARD VIEWS
###############################################

@login_required
def leaderboards(request):

    # User's ranking for position on global leaderboard.
    ranking = utils.get_user_ranking(request.user)
    franking = utils.get_user_franking(request.user)

    user_leaderboard_set = set(request.user.leaderboard_set.values_list('name',flat=True))
    all_lb = Leaderboard.objects.all().order_by(Lower('name'))

    public_lb = Leaderboard.objects.prefetch_related('users').filter(users=request.user, is_private=False)
    private_lb = Leaderboard.objects.prefetch_related('users').filter(users=request.user, is_private=True)

    # Code taken from https://simpleisbetterthancomplex.com/tutorial/2016/08/03/how-to-paginate-with-django.html
    page = request.GET.get('page', 1)
    all_lb_subset = paginated_data(all_lb, num_per_page=5, page=page)

    context_dict = {
        'ranking': ranking,
        'franking': franking,
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
        search_term = request.POST.get('search_term', None)

        if search_term == '' or search_term is None:
            all_lb = Leaderboard.objects.all().order_by(Lower('name'))
        else:
            all_lb = Leaderboard.objects.filter(name__contains=search_term).order_by(Lower('name'))

        page = request.POST.get('page', 1)
        all_lb_subset = paginated_data(all_lb, num_per_page=5, page=page)

        user_leaderboard_set = set(request.user.leaderboard_set.values_list('name',flat=True))        
        context_dict = { 
            'leaderboards': all_lb_subset, 
            'all_boards': True,
            'user_leaderboard_set': user_leaderboard_set,
        }
        data = {
            'result': render_to_string('include_leaderboards.html', context_dict)
        }
        return JsonResponse(data)

@login_required
@csrf_exempt
def search_leaderboards(request):
    if request.is_ajax():
        search_term = request.POST.get('search_term', None)

        # Filter leaderboards by the search term
        if search_term == '' or search_term is None:
            matched_lbs = Leaderboard.objects.order_by(Lower("name"))
        else:
            matched_lbs = Leaderboard.objects.filter(name__contains=search_term).order_by(Lower("name"))

        page = request.POST.get('page', 1)
        matched_lb_subset = paginated_data(matched_lbs, num_per_page=5, page=page)

        user_leaderboard_set = set(request.user.leaderboard_set.values_list('name',flat=True))
        
        context_dict = { 
            'leaderboards': matched_lb_subset, 
            'all_boards': True,
            'user_leaderboard_set': user_leaderboard_set,
        }
        data = {
            'result': render_to_string('include_leaderboards.html', context_dict)
        }
        return JsonResponse(data)

@login_required
def show_leaderboard(request, leaderboard):

    try:
        # Get leaderboard with given slug.
        leaderboard = Leaderboard.objects.prefetch_related('users', 'users__profile').get(slug=leaderboard)

        # If there are errors, do not reinitialise the form.
        access_form = PrivateAccessForm(request.POST or None)
        context_dict = {'access_form': access_form, 'leaderboard': leaderboard}

        # Check if the request was HTTP POST.
        if request.method == 'POST':

            # Check if the provided form is valid.
            if access_form.is_valid():

                given_password = access_form.cleaned_data['password']

                if check_password(given_password, leaderboard.password):
                    leaderboard.users.add(request.user)
                    leaderboard.save()
                    return HttpResponseRedirect(reverse('show_leaderboard', kwargs={'leaderboard':leaderboard.slug}))
     

        if leaderboard.is_private and not request.user in leaderboard.users.all():
            return render(request, 'private_leaderboard_login.html', context_dict)

        # Get stats for the given leaderboard
        stats = leaderboard_stats(leaderboard)

        # Add entities to the context dictionary, unpacking the stats into the dictionary.
        context_dict = {
            'access_form': access_form,
            'leaderboard':leaderboard, 
            **stats
        }

        # daily_user_stats = utils.user_daily_performance(leaderboard)
        # if daily_user_stats is not None:
        #    context_dict['best_users'] = daily_user_stats['best_users']
        #    context_dict['best_points'] = daily_user_stats['best_points']

    except Leaderboard.DoesNotExist:
        # We get here if we couldn't find the specified game
        messages.error(request, "No leaderboard with name \'{}\' could be found".format(leaderboard))
        return HttpResponseRedirect(reverse('leaderboards'))

    return render(request, 'show_leaderboard.html', context_dict)

# Global leaderboard for all users in the system
@login_required
def global_leaderboard(request):
    stats = leaderboard_stats()
    global_leaderboard = True # Allows us to conditionally render/unrender parts of the template
    
    # Pagination stuff goes here

    context = {
        'global_leaderboard': global_leaderboard,
        **stats
    }

    #daily_user_stats = utils.user_daily_performance()
    #if daily_user_stats is not None:
    #    context['best_users'] = daily_user_stats['best_users']
    #    context['best_points'] = daily_user_stats['best_points']

    return render(request, "show_leaderboard.html", context)

# Global leaderboard for all users in the system
@login_required
def friends_leaderboard(request):
    stats = leaderboard_stats("Friends", user=request.user)
    friends_leaderboard = True # Allows us to conditionally render/unrender parts of the template
    
    # Pagination stuff goes here

    context = {
        'friends_leaderboard': friends_leaderboard,
        **stats
    }

    return render(request, "show_leaderboard.html", context)

# Returns stats for the leaderboard passed in. If leaderboard is None, we assume global leaderboard
# This may need altered when friend lists are added, to accommodate the extra option.
def leaderboard_stats(leaderboard=None, user=None):
    if leaderboard is None:
        members = get_user_model().objects.select_related('profile').order_by('-profile__points')
    elif leaderboard == "Friends":
        members = user.profile.friends.all().select_related('profile').order_by('-profile__points') | get_user_model().objects.filter(username=user)
    else:
        members = leaderboard.users.select_related('profile').order_by('-profile__points')
    # Get a collection of board statistics.
    total_points = members.aggregate(tp=Sum('profile__points'))['tp']

    # Create the stats dictionary
    stats_dict = { 'members': members, 'total_points': total_points }
    if members:
        membercount = members.count()
        average_points = total_points / membercount
        percent_above_average = members.filter(profile__points__gte=average_points).count()*100 / membercount
    else:
        average_points = percent_above_average = 0
    # Update the stats dict and return it
    stats_dict.update({
        'average_points': average_points, 
        'percent_above_average': percent_above_average,
    })
    return stats_dict


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