from django.db.models.functions import Rank
from django.db.models.expressions import Window
from django.db.models import F
from django.contrib.auth import get_user_model
from django.utils import timezone

import logging
import datetime
from itertools import groupby

logger = logging.getLogger(__name__)
"""
Utility methods for common/complex tasks
"""

def get_next_games(number=3):
    from .models import Fixture
    """ Returns the next games to be played, the number of which can be specified, but which defaults to 3 """

    cur_date = timezone.now()
    # Since the Fixture model's default ordering is by match_date, we can just take a slice of the query results
    fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_NOT_PLAYED)[:number]
    for fixture in fixtures:
        assert cur_date < fixture.match_date # If this fails, something has gone wrong.
    return fixtures

def get_last_results(number=3):
    from .models import Fixture
    """ Returns the last games to be played, the number of which can be specified, but which defaults to 3 """
    cur_date = timezone.now()
    fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_PLAYED).reverse()[:number]
    for fixture in fixtures:
        assert cur_date > fixture.match_date
    return fixtures

def get_user_ranking(user):
    """
    Takes a user, and returns their rank in the system compared to other users. Based on the user's points field.
    """

    ranked_users = group_users_by_points() # Groups users into sublists: each sublist has users with the same number of points.
    
    # Iterates over the ranked sublists, finds which one the user is in, and returns the ranking
    ranking = 1
    for grouping in ranked_users:
        if user in grouping:
            return ranking
        else:
            ranking += len(grouping) # Increment the ranking by however many users were in the previous sublist
    return None

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
        fixtures = Fixture.all_completed_fixtures()

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
                add_user_points(user, ans, total_points)
            elif update:
                # If the fixture is updated, get the difference between the updated-points, and the original (total_points)
                if saved_fixture is not None:
                    new_points = calculate_points(saved_fixture, ans)
                    pointsdelta = new_points - total_points
                    update_user_points(user, pointsdelta)
            elif remove:
                # If the fixture is removed, remove the points given for the answer
                rm_user_points(user, ans, total_points)

def add_user_points(user, answer, pts):
    """
    Adds points for the provided user, if the points_added flag is set to POINTS_NOT_ADDED
    """
    # Add points to user's total.
    if not answer.points_added:
        user.profile.points = F('points') + pts
        user.save()
        user.refresh_from_db()

    # Update answer entry so points for this fixture aren't given to the user in the future.
    answer.points_added = answer.POINTS_ADDED
    answer.save()
    answer.refresh_from_db()


def update_user_points(user, pts):
    """ Updates the points already given out to a user based on an altered scoreline.

        user -> the user who provided the answer
        pts -> the difference between the points for the updated fixture, vs the points from the original fixture     
    """
    user.profile.points = F('points') + pts
    user.save()
    user.refresh_from_db()

def rm_user_points(user, answer, pts):
    """ Removes a user's points for a given answer, and resets the points_added flag to False """
    if answer.points_added:
        user.profile.points = F('points') - pts
        user.save()
        user.refresh_from_db()
        answer.points_added = answer.POINTS_NOT_ADDED
        answer.save()
        answer.refresh_from_db()

def calculate_points(fixture, answer):
    """
    Takes a Fixture and its associated Answer, and calculates the points to be given for the user who added the Answer
    """
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
        total_points += 5

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
            total_points += 2

        # Check the total goals scored or the goal difference is correct (can't have both, or the prediction would be correct).
        if ((user_total_goals == actual_total_goals) or (user_goal_difference == actual_goal_difference)):
            total_points += 1

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
        total_points = 0
        for answer in answers:
            total_points += calculate_points(answer.fixture, answer)
        if not total_points == user.profile.points:
            logger.error("User {} has {} points, but should have {} points".format(user, user.profile.points, total_points))
        assert total_points == user.profile.points

def stage_is_finished(stage):
    """ Given a stage (ie, group, last 16, quarter final, etc), determines whether it has been finished or not """
    from socapp.models import Fixture
    final_fixture = Fixture.all_fixtures_by_stage(stage).last()
    if final_fixture is not None:
        # If the current time is after the last-fixture's matchdate, then the stage is finished
        return final_fixture.match_date < timezone.now()
    return False # If no fixtures, return false

def stage_completion_date(stage):
    """ Given a stage (ie, group, last 16, quarter final, etc), determines (roughly) the date and time of completion """
    from socapp.models import Fixture
    final_fixture = Fixture.all_fixtures_by_stage(stage).last()
    if final_fixture is not None:
        delta = datetime.timedelta(hours=2) # Probably change: currently set to 2 hours after the last match's kickoff
        return final_fixture.match_date + delta

# Helper that determines if the outcome of a fixture is the same as it was previously, or not
def same_result(fixture1, fixture2):
    if fixture1.result_available() and fixture2.result_available():
        if fixture1.get_winner() == fixture2.get_winner():
            return True
        if fixture1.is_draw() and fixture2.is_draw():
            return True
    return False
