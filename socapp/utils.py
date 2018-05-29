from django.db.models.functions import Rank
from django.db.models.expressions import Window
from django.db.models import F
from django.contrib.auth import get_user_model
from django.utils import timezone

from itertools import groupby

from .models import *

"""
Utility methods for common/complex tasks
"""

def get_next_games(number=3):
    """ Returns the next games to be played, the number of which can be specified, but which defaults to 3 """

    cur_date = timezone.now()
    # Since the Fixture model's default ordering is by match_date, we can just take a slice of the query results
    fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_NOT_PLAYED)[:number]
    for fixture in fixtures:
        assert cur_date < fixture.match_date # If this fails, something has gone wrong.
    return fixtures

def get_last_results(number=3):
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
    team.games_played = F('games_played') + 1

    if fixture.get_winner() == team:
        team.games_won = F('games_won') + 1
    elif fixture.get_loser() == team:
        team.games_lost = F('games_lost') + 1
    elif fixture.is_draw():
        team.games_drawn = F('games_drawn') + 1

    if fixture.team1 == team:
        team.goals_for = F('goals_for') + fixture.team1_goals
        team.goals_against = F('goals_against') + fixture.team2_goals
    else:
        team.goals_for = F('goals_for') + fixture.team2_goals
        team.goals_against = F('goals_against') + fixture.team1_goals
    
    team.save()
    team.refresh_from_db()

# Removes the result data from the team model's fields, either directly (goals for, goals against) or by inference (games won/drawn/lost)
def remove_team_data(fixture, team):
    team.games_played = F('games_played') - 1

    if fixture.get_winner() == team:
        team.games_won = F('games_won') - 1
    elif fixture.get_loser() == team:
        team.games_lost = F('games_lost') - 1
    elif fixture.is_draw():
        team.games_drawn = F('games_drawn') - 1

    if fixture.team1 == team:
        team.goals_for = F('goals_for') - fixture.team1_goals
        team.goals_against = F('goals_against') - fixture.team2_goals
    elif fixture.team2 == team:
        team.goals_for = F('goals_for') - fixture.team2_goals
        team.goals_against = F('goals_against') - fixture.team1_goals
    
    team.save()
    team.refresh_from_db()

# Compares the previously saved fixture with the newly saved fixture in order to update the relevant fields in the Team model
def update_team_data(previous_fixture, updated_fixture, team):
    # Determine if the result is the same as the previous fixture. If so, only the goals for/against fields need updating
    if same_result(previous_fixture, updated_fixture):
        update_goals_fields(previous_fixture, updated_fixture, team)
    else:
        update_result_fields(previous_fixture, updated_fixture, team)
        update_goals_fields(previous_fixture, updated_fixture, team)
    team.save()
    team.refresh_from_db()

# Helper that determines if the outcome of a fixture is the same as it was previously, or not
def same_result(fixture1, fixture2):
    if fixture1.result_available() and fixture2.result_available():
        if fixture1.get_winner() == fixture2.get_winner():
            return True
        if fixture1.is_draw() and fixture2.is_draw():
            return True
    return False

# Updates the games_won, games_drawn, games_lost fields in the Team model passed in
def update_result_fields(previous_fixture, updated_fixture, team):
    if previous_fixture.is_draw() and not updated_fixture.is_draw():
        team.games_drawn = F('games_drawn') - 1
    if not previous_fixture.is_draw() and updated_fixture.is_draw():
        team.games_drawn = F('games_drawn') + 1
    if previous_fixture.get_winner() == team and not updated_fixture.get_winner() == team:
        team.games_won = F('games_won') - 1
    if not previous_fixture.get_winner() == team and updated_fixture.get_winner() == team:
        team.games_won = F('games_won') + 1
    if previous_fixture.get_loser() == team and not updated_fixture.get_loser() == team:
        team.games_lost = F('games_lost') - 1
    if not previous_fixture.get_loser() == team and updated_fixture.get_loser() == team:
        team.games_lost = F('games_lost') + 1
    return team

# Updates the goals_for, goals_against fields in the Team model passed in
def update_goals_fields(previous_fixture, updated_fixture, team):
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
    elif gf_diff > 0:
        team.goals_for = F('goals_for') - gf_diff
    
    if ga_diff < 0:
        team.goals_against = F('goals_against') + abs(ga_diff)
    elif ga_diff > 0:
        team.goals_against = F('goals_against') - ga_diff