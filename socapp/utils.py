from django.db.models.functions import Rank
from django.db.models.expressions import Window
from django.db.models import F, Sum
from django.contrib.auth import get_user_model
from django.utils import timezone

import logging
import datetime
from itertools import groupby

logger = logging.getLogger(__name__)
"""
Utility methods for common/complex tasks
"""

def group_users_by_points(users_queryset=None):
    """ 
    Orders a queryset of users into groups based on the points each user has accumulated.
    The queryset defaults to every user in the application, but the function can be passed a subset of users.
    Returns a two dimensional list, with each inner list containing users in that particular points grouping.
    The list is ordered from highest points grouping, through to lowest
    """

    if users_queryset is None:
        User = get_user_model()
        users = User.objects.select_related('profile').order_by('-profile__points')
    else:
        users = users_queryset

    # points_rank = Window(expression=Rank(), partition_by=F('profile__id'), order_by=F('profile__points').desc())

    users_grouped_by_points = []

    for k,v in groupby(users, key=lambda u: u.profile.points):
        users_grouped_by_points.append(list(v))

    return users_grouped_by_points

# Finds any fixtures for which the user has not made a prediction
def get_fixtures_with_no_prediction(user, stage=None):
    from socapp.models import Answer, Fixture
    user_predictions = Answer.objects.select_related('user').filter(user=user).values('fixture')
    if stage is not None:
        fixtures = Fixture.objects.filter(stage=stage).exclude(pk__in=user_predictions)
    else:
        fixtures = Fixture.objects.exclude(pk__in=user_predictions)
    return fixtures

# Daily movement stats for a leaderboard. If no leaderboard is provided, assumes global leaderboard
def user_daily_performance(leaderboard=None):
    from socapp.models import Fixture, Answer
    user_set = leaderboard.users.all() if leaderboard is not None else get_user_model().objects.all()
    fixtures = Fixture.todays_fixtures().filter(status=Fixture.MATCH_STATUS_PLAYED)
    if fixtures.exists():
        daily_points = Answer.objects.select_related('fixture', 'user').filter(user__in=user_set, fixture__in=fixtures) \
            .values_list('user').annotate(pts=Sum('points'))
        
        # If there are no predictions for any of these games, return None
        if len(daily_points) == 0:
            return None
        else:
            best_users = []
            worst_users = []
            max_pts = min_pts = 0
            for user, points in daily_points:
                if len(best_users) == 0:
                    best_users.append(get_user_model().objects.get(pk=user))
                    worst_users.append(get_user_model().objects.get(pk=user))
                    max_pts = min_pts = points
                elif points > max_pts:
                    best_users = [get_user_model().objects.get(pk=user)]
                    max_pts = points
                elif points == max_pts:
                    best_users.append(get_user_model().objects.get(pk=user))
                elif points < min_pts:
                    worst_users = [get_user_model().objects.get(pk=user)]
                    min_pts = points
                elif points == min_pts:
                    worst_users.append(get_user_model().objects.get(pk=user))
            
            return {
                'best_users': best_users, 
                'worst_users': worst_users, 
                'best_points': max_pts, 
                'worst_points': min_pts
            }
    return None
    

######
# Methods for updating the two associated Team model instances whenever a Fixture is updated with a result

# Adds the result data to the team model's fields, either directly (goals for, goals against) or by inference (games won/drawn/lost)
def add_team_data(fixture, team):
    from socapp.models import Fixture
    team.games_played = F('games_played') + 1

    if fixture.get_winner() == team:
        team.games_won = F('games_won') + 1
        if fixture.stage == Fixture.GROUP:
            team.group_won = F('group_won') + 1
        else:
            team.group_won = F('group_won')
    else:
        team.games_won = F('games_won')
        team.group_won = F('group_won')

    if fixture.get_loser() == team:
        team.games_lost = F('games_lost') + 1
        if fixture.stage == Fixture.GROUP:
            team.group_lost = F('group_lost') + 1
        else:
            team.group_lost = F('group_lost')
    else:
        team.games_lost = F('games_lost')
        team.group_lost = F('group_lost')

    if fixture.is_draw():
        team.games_drawn = F('games_drawn') + 1
        if fixture.stage == Fixture.GROUP:
            team.group_drawn = F('group_drawn') + 1
        else:
            team.group_drawn = F('group_drawn')
    else:
        team.games_drawn = F('games_drawn')
        team.group_drawn = F('group_drawn')
    
    # Add for group won
    if fixture.team1 == team:
        team.goals_for = F('goals_for') + fixture.team1_goals
        team.goals_against = F('goals_against') + fixture.team2_goals
        if fixture.stage == Fixture.GROUP:
            team.group_goals_for = F('group_goals_for') + fixture.team1_goals
            team.group_goals_against = F('group_goals_against') + fixture.team2_goals
        else:
            team.group_goals_for = F('group_goals_for')
            team.group_goals_against = F('group_goals_against')
    else:
        team.goals_for = F('goals_for') + fixture.team2_goals
        team.goals_against = F('goals_against') + fixture.team1_goals
        if fixture.stage == Fixture.GROUP:
            team.group_goals_for = F('group_goals_for') + fixture.team2_goals
            team.group_goals_against = F('group_goals_against') + fixture.team1_goals
        else:
            team.group_goals_for = F('group_goals_for')
            team.group_goals_against = F('group_goals_against')
    
    team.save()
    team.refresh_from_db()

# Removes the result data from the team model's fields, either directly (goals for, goals against) or by inference (games won/drawn/lost)
def remove_team_data(fixture, team):
    from socapp.models import Fixture

    team.games_played = F('games_played') - 1

    if fixture.get_winner() == team:
        team.games_won = F('games_won') - 1
        if fixture.stage == Fixture.GROUP:
            team.group_won = F('group_won') - 1
        else:
            team.group_won = F('group_won')
    else:
        team.games_won = F('games_won')
        team.group_won = F('group_won')

    if fixture.get_loser() == team:
        team.games_lost = F('games_lost') - 1
        if fixture.stage == Fixture.GROUP:
            team.group_lost = F('group_lost') - 1
        else:
            team.group_lost = F('group_lost')
    else:
        team.games_lost = F('games_lost')
        team.group_lost = F('group_lost')
    
    if fixture.is_draw():
        team.games_drawn = F('games_drawn') - 1
        if fixture.stage == Fixture.GROUP:
            team.group_drawn = F('group_drawn') - 1
        else:
            team.group_drawn = F('group_drawn')
    else:
        team.games_drawn = F('games_drawn')
        team.group_drawn = F('group_drawn')

    if fixture.team1 == team:
        team.goals_for = F('goals_for') - fixture.team1_goals
        team.goals_against = F('goals_against') - fixture.team2_goals
        if fixture.stage == Fixture.GROUP:
            team.group_goals_for = F('group_goals_for') - fixture.team1_goals
            team.group_goals_against = F('group_goals_against') - fixture.team2_goals
        else:
            team.group_goals_for = F('group_goals_for')
            team.group_goals_against = F('group_goals_against')

    elif fixture.team2 == team:
        team.goals_for = F('goals_for') - fixture.team2_goals
        team.goals_against = F('goals_against') - fixture.team1_goals
        if fixture.stage == Fixture.GROUP:
            team.group_goals_for = F('group_goals_for') - fixture.team2_goals
            team.group_goals_against = F('group_goals_against') - fixture.team1_goals
        else:
            team.group_goals_for = F('group_goals_for')
            team.group_goals_against = F('group_goals_against')
    
    team.save()
    team.refresh_from_db()

# Compares the previously saved fixture with the newly saved fixture in order to update the relevant fields in the Team model
def update_team_data(previous_fixture, updated_fixture, team):
    update_result_fields(previous_fixture, updated_fixture, team)
    update_goals_fields(previous_fixture, updated_fixture, team)
    team.save()
    team.refresh_from_db()

# Updates the games_won, games_drawn, games_lost fields in the Team model passed in
def update_result_fields(previous_fixture, updated_fixture, team):
    from socapp.models import Fixture

    if previous_fixture.is_draw() and not updated_fixture.is_draw():
        team.games_drawn = F('games_drawn') - 1
        if previous_fixture.stage == Fixture.GROUP:
            team.group_drawn = F('group_drawn') - 1
        else:
            team.group_drawn = F('group_drawn')

    elif not previous_fixture.is_draw() and updated_fixture.is_draw():
        team.games_drawn = F('games_drawn') + 1
        if previous_fixture.stage == Fixture.GROUP:
            team.group_drawn = F('group_drawn') + 1
        else:
            team.group_drawn = F('group_drawn')
    else:
        team.games_drawn = F('games_drawn')
        team.group_drawn = F('group_drawn')

    if previous_fixture.get_winner() == team and not updated_fixture.get_winner() == team:
        team.games_won = F('games_won') - 1
        if previous_fixture.stage == Fixture.GROUP:
            team.group_won = F('group_won') - 1
        else:
            team.group_won = F('group_won')
    elif not previous_fixture.get_winner() == team and updated_fixture.get_winner() == team:
        team.games_won = F('games_won') + 1
        if previous_fixture.stage == Fixture.GROUP:
            team.group_won = F('group_won') + 1
        else:
            team.group_won = F('group_won')
    else:
        team.games_won = F('games_won')
        team.group_won = F('group_won')

    if previous_fixture.get_loser() == team and not updated_fixture.get_loser() == team:
        team.games_lost = F('games_lost') - 1
        if previous_fixture.stage == Fixture.GROUP:
            team.group_lost = F('group_lost') - 1
        else:
            team.group_lost = F('group_lost')
    elif not previous_fixture.get_loser() == team and updated_fixture.get_loser() == team:
        team.games_lost = F('games_lost') + 1
        if previous_fixture.stage == Fixture.GROUP:
            team.group_lost = F('group_lost') + 1
        else:
            team.group_lost = F('group_lost')
    else:
        team.games_lost = F('games_lost')
        team.group_lost = F('group_lost')

# Updates the goals_for, goals_against fields in the Team model passed in
def update_goals_fields(previous_fixture, updated_fixture, team):
    from socapp.models import Fixture

    if team == previous_fixture.team1:
        gf_diff = previous_fixture.team1_goals - updated_fixture.team1_goals
        ga_diff = previous_fixture.team2_goals - updated_fixture.team2_goals
    elif team == previous_fixture.team2:
        gf_diff = previous_fixture.team2_goals - updated_fixture.team2_goals
        ga_diff = previous_fixture.team1_goals - updated_fixture.team1_goals

    # For the goals_for and goals_against fields, if the difference is less than 0, that means the team has scored/conceded more goals in the updated result.
    # Increment by the absolute value of the difference.
    # If the difference is more than 0, then the team has less goals in the updated result.
    # In this case, take the extra goals from the initial fixture away from the updated fixture.
    if gf_diff < 0:
        team.goals_for = F('goals_for') + abs(gf_diff)
        if previous_fixture.stage == Fixture.GROUP:
            team.group_goals_for = F('group_goals_for') + abs(gf_diff)
        else:
            team.group_goals_for = F('group_goals_for')        
    elif gf_diff > 0:
        team.goals_for = F('goals_for') - gf_diff
        if previous_fixture.stage == Fixture.GROUP:
            team.group_goals_for = F('group_goals_for') - gf_diff
        else:
            team.group_goals_for = F('group_goals_for') 
    else:
        team.goals_for = F('goals_for')
        team.group_goals_for = F('group_goals_for')
    
    if ga_diff < 0:
        team.goals_against = F('goals_against') + abs(ga_diff)
        if previous_fixture.stage == Fixture.GROUP:
            team.group_goals_against = F('group_goals_against') + abs(ga_diff)
        else:
            team.group_goals_against = F('group_goals_against')  
    elif ga_diff > 0:
        team.goals_against = F('goals_against') - ga_diff
        if previous_fixture.stage == Fixture.GROUP:
            team.group_goals_against = F('group_goals_against') - ga_diff
        else:
            team.group_goals_against = F('group_goals_against')  
    else:
        team.goals_against = F('goals_against')
        team.group_goals_against = F('group_goals_against') 

###############################
### USER POINTS CALCULATION
###############################

# Access tournament via saved fixture
def update_user_pts(saved_fixture=None, prev_fixture=None, add=False, update=False, remove=False):
    """
    Calculates all users' points for the given fixture, or all played fixtures. 
    The method is capable of adding, updating and removing points based on the params passed in.
    """
    from .models import Answer, Fixture

    # Set the fixture based on what (if any) fixtures were passed in. Default to all fixtures already played.
    if add and saved_fixture is not None:
        fixtures = [saved_fixture]
    elif (remove or update) and prev_fixture is not None:
        fixtures = [prev_fixture]
    else:
        fixtures = Fixture.all_completed_fixtures() # preferably never use this

    # For the given fixture(s), add points for each user with answers relating to that fixture.
    for user in get_user_model().objects.all():
        for fixture in fixtures:
            # Get user's answer for each completed fixture. If no answer exists then continue to the next fixture.
            try:
                ans = Answer.objects.select_related('fixture','user') \
                        .get(fixture=fixture, user=user)
            except Answer.DoesNotExist:
                continue

            # Get the points to be given to this answer
            total_points = calculate_points(fixture, ans)

            # Determine the operation to perform in order to update user points, and act accordingly.
            if add:
                # If the fixture is added, add the points given for the answer
                add_user_points(user, ans, total_points, fixture.tournament)
            elif update:
                # If the fixture is updated, get the difference between the updated-points, and the original (total_points)
                if saved_fixture is not None:
                    new_points = calculate_points(saved_fixture, ans)
                    pointsdelta = new_points - total_points
                    update_user_points(user, ans, pointsdelta, fixture.tournament)
            elif remove:
                # If the fixture is removed, remove the points given for the answer
                rm_user_points(user, ans, total_points, fixture.tournament)

def add_user_points(user, answer, pts, tournament):
    """
    Adds points for the provided user, if the points_added flag is set to POINTS_NOT_ADDED
    """
    from socapp_auth.models import TournamentPoints
    # Add points to user's total. The if condition should always be evaluate to true.
    if not answer.points_added:
        user.profile.points = F('points') + pts
        user.save()
        user.refresh_from_db()

        if TournamentPoints.objects.filter(user=user.profile, tournament=tournament).exists():
            t_pts = TournamentPoints.objects.filter(user=user.profile, tournament=tournament)
            t_pts.update(points = F('points') + pts)
        else:
            t_pts = TournamentPoints.objects.create(user=user.profile, tournament=tournament, points=pts)

        answer.points = pts
        answer.points_added = answer.POINTS_ADDED
        answer.save()
        answer.refresh_from_db()


def update_user_points(user, ans, pts, tournament):
    """ Updates the points already given out to a user based on an altered scoreline.

        user -> the user who provided the answer
        pts -> the difference between the points for the updated fixture, vs the points from the original fixture     
    """
    from socapp_auth.models import TournamentPoints
    user.profile.points = F('points') + pts
    user.save()
    user.refresh_from_db()

    if TournamentPoints.objects.filter(user=user.profile, tournament=tournament).exists():
        t_pts = TournamentPoints.objects.filter(user=user.profile, tournament=tournament)
        t_pts.update(points = F('points') + pts)

    ans.points = F('points') + pts
    ans.save()
    ans.refresh_from_db()

def rm_user_points(user, answer, pts, tournament):
    """ Removes a user's points for a given answer, and resets the points_added flag to False """
    from socapp_auth.models import TournamentPoints
    if answer.points_added:
        user.profile.points = F('points') - pts
        user.save()
        user.refresh_from_db()

        if TournamentPoints.objects.filter(user=user.profile, tournament=tournament).exists():
            t_pts = TournamentPoints.objects.filter(user=user.profile, tournament=tournament)
            t_pts.update(points = F('points') - pts)

        answer.points_added = answer.POINTS_NOT_ADDED
        answer.points = None
        answer.save()
        answer.refresh_from_db()

def calculate_points(fixture, answer):
    """
    Takes a Fixture and its associated Answer, and calculates the points to be given for the user who added the Answer
    """

    # List of points available.
    ANSWER_RESULT = 5
    ANSWER_OUTCOME = 2
    ANSWER_BONUS = 1

    # Get actual and predicted goals scored for each team in the fixture
    user_team1_goals = answer.team1_goals
    user_team2_goals = answer.team2_goals
    actual_team1_goals = fixture.team1_goals
    actual_team2_goals = fixture.team2_goals

    # Set total points to zero. This value will be returned by the function after calculation below.
    total_points = 0

    # First check if result is correct, i.e. prediction of goals scored for each time match.
    team1_accuracy = user_team1_goals - actual_team1_goals
    team2_accuracy = user_team2_goals - actual_team2_goals

    if (team1_accuracy == team2_accuracy == 0):
        total_points += ANSWER_RESULT

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
            (user_goal_difference == actual_goal_difference)): 
            total_points += ANSWER_OUTCOME

        # Check the total goals scored or the goal difference is correct (can't have both, or the prediction would be correct).
        if ((user_total_goals == actual_total_goals) or (user_goal_difference == actual_goal_difference)):
            total_points += ANSWER_BONUS

    # Calculate additional points for fixtures which can go to extra time/penalties.
    if (fixture.can_be_over_90):
        if (answer.has_extra_time):
            if (fixture.has_extra_time):
                total_points += ANSWER_OUTCOME
            else:
                total_points -= ANSWER_BONUS

        if (answer.has_penalties):
            if (fixture.has_penalties):
                total_points += ANSWER_OUTCOME
            else:
                total_points -= ANSWER_BONUS

    return total_points


def sync_user_points():
    """
    This function (or something similar) can be run AFTER a fixture is played, in order to ensure there are no anomalies in the user points. 
    It looks at all matches that've been played, and calculates the user's points for each, comparing them to the actual points in the database.
    These fields should sync, and if not, an error should be logged.
    Preferably execute this function periodically (ie - 20 mins after each match finishes) with Celery or Cron.
    """
    from .models import Answer, Fixture

    fixtures = Fixture.all_completed_fixtures()
    users = get_user_model().objects.all()
    for user in users:
        answers = Answer.objects.filter(user=user, fixture__in=fixtures)
        answers_points_field_total = answers.aggregate(total=Sum('points'))['total']
        total_points = 0
        for answer in answers:
            total_points += calculate_points(answer.fixture, answer)
        if not total_points == user.profile.points == answers_points_field_total:
            logger.warning("User {} has {} points, but should have {} points".format(user, user.profile.points, total_points))
        assert total_points == user.profile.points

def stage_is_finished(tournament, stage):
    """ Given a stage (ie, group, last 16, quarter final, etc), determines whether it has been finished or not """
    from socapp.models import Fixture
    return stage_completion_date(tournament, stage) < timezone.now()

def stage_completion_date(tournament, stage):
    """ Given a stage (ie, group, last 16, quarter final, etc), determines (roughly) the date and time of completion """
    from socapp.models import Fixture
    final_fixture = tournament.all_fixtures_by_stage(stage).last()
    if final_fixture is not None:
        delta = datetime.timedelta(hours=2) # Probably change: currently set to 2 hours after the last match's kickoff
        return final_fixture.match_date + delta
    return None

# Helper that determines if the outcome of a fixture is the same as it was previously, or not
def same_result(fixture1, fixture2):
    if fixture1.result_available() and fixture2.result_available():
        if fixture1.get_winner() == fixture2.get_winner():
            return True
        if fixture1.is_draw() and fixture2.is_draw():
            return True
    return False
