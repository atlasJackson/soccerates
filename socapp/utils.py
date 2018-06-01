from django.db.models.functions import Rank
from django.db.models.expressions import Window
from django.db.models import F
from django.contrib.auth import get_user_model
from django.utils import timezone

from itertools import groupby

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
        if fixture.stage == Fixture.Group:
            team.group_won = F('group_won') + 1
        else:
            team.group_won = F('group_won')
    else:
        team.games_won = F('games_won')
        team.group_won = F('group_won')

    if fixture.get_loser() == team:
        team.games_lost = F('games_lost') + 1
        if fixture.stage == Fixture.Group:
            team.group_lost = F('group_lost') + 1
        else:
            team.group_lost = F('group_lost')
    else:
        team.games_lost = F('games_lost')
        team.group_lost = F('group_lost')

    if fixture.is_draw():
        team.games_drawn = F('games_drawn') + 1
        if fixture.stage == Fixture.Group:
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
        if fixture.stage == Fixture.Group:
            team.group_goals_for = F('group_goals_for') + fixture.team1_goals
            team.group_goals_against = F('group_goals_against') + fixture.team2_goals
        else:
            team.group_goals_for = F('group_goals_for')
            team.group_goals_against = F('group_goals_against')
    else:
        team.goals_for = F('goals_for') + fixture.team2_goals
        team.goals_against = F('goals_against') + fixture.team1_goals
        if fixture.stage == Fixture.Group:
            team.group_goals_for = F('group_goals_for') + fixture.team2_goals
            team.group_goals_against = F('group_goals_against') + fixture.team1_goals
        else:
            team.group_goals_for = F('group_goals_for')
            team.group_goals_against = F('group_goals_against')
    
    team.save()
    team.refresh_from_db()

# Removes the result data from the team model's fields, either directly (goals for, goals against) or by inference (games won/drawn/lost)
def remove_team_data(fixture, team):
    team.games_played = F('games_played') - 1

    if fixture.get_winner() == team:
        team.games_won = F('games_won') - 1
    else:
        team.games_won = F('games_won')

    if fixture.get_loser() == team:
        team.games_lost = F('games_lost') - 1
    else:
        team.games_lost = F('games_lost')
    
    if fixture.is_draw():
        team.games_drawn = F('games_drawn') - 1
    else:
        team.games_drawn = F('games_drawn')

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
    update_result_fields(previous_fixture, updated_fixture, team)
    update_goals_fields(previous_fixture, updated_fixture, team)
    team.save()
    team.refresh_from_db()

# Updates the games_won, games_drawn, games_lost fields in the Team model passed in
def update_result_fields(previous_fixture, updated_fixture, team):
    if previous_fixture.is_draw() and not updated_fixture.is_draw():
        team.games_drawn = F('games_drawn') - 1
    elif not previous_fixture.is_draw() and updated_fixture.is_draw():
        team.games_drawn = F('games_drawn') + 1
    else:
        team.games_drawn = F('games_drawn')

    if previous_fixture.get_winner() == team and not updated_fixture.get_winner() == team:
        team.games_won = F('games_won') - 1
    elif not previous_fixture.get_winner() == team and updated_fixture.get_winner() == team:
        team.games_won = F('games_won') + 1
    else:
        team.games_won = F('games_won')

    if previous_fixture.get_loser() == team and not updated_fixture.get_loser() == team:
        team.games_lost = F('games_lost') - 1
    elif not previous_fixture.get_loser() == team and updated_fixture.get_loser() == team:
        team.games_lost = F('games_lost') + 1
    else:
        team.games_lost = F('games_lost')
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
    else:
        team.goals_for = F('goals_for')
    
    if ga_diff < 0:
        team.goals_against = F('goals_against') + abs(ga_diff)
    elif ga_diff > 0:
        team.goals_against = F('goals_against') - ga_diff
    else:
        team.goals_against = F('goals_against')

###############################
### USER POINTS CALCULATION
###############################

# This will need to be moved to another process, as it will have to perform a calculation for every user in the system.
def update_user_pts(fixture=None):
    for user in get_user_model().objects.all():
        calculate_user_points(user,fixture)

# Calculates the user's points for games that have already been played, but have not yet been added to the user's points total.
def calculate_user_points(user, fixture=None):
    from .models import Answer, Fixture

    # Get completed fixtures.
    if fixture is not None:
        fixtures = [fixture]
    else:
        fixtures = Fixture.all_completed_fixtures()
            
    for fixture in fixtures:
        # Get user's answer for each completed fixture. If no answer exists then continue to the next fixture.
        try:
            ans = Answer.objects.select_related('fixture','user') \
                    .get(fixture=fixture, user=user)
        except Answer.DoesNotExist:
            continue

        # Skip fixture if points have been added.
        if ans.points_added:
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
           # print("exact")
            add_user_points(user, ans, 5)

        # If not, then check for other conditions to get points. 
        else:
           # print("not exact")
            # Get actual/predicted total goals, and actual/predicted goal difference.
            user_total_goals = user_team1_goals + user_team2_goals
            actual_total_goals = actual_team1_goals + actual_team2_goals
            user_goal_difference = user_team1_goals - user_team2_goals
            actual_goal_difference = actual_team1_goals - actual_team2_goals

            # Check the result is correct
            if ((user_goal_difference > 0 and actual_goal_difference > 0) or
                (user_goal_difference < 0 and actual_goal_difference < 0) or
                (user_goal_difference == actual_goal_difference)): 
                #print("result correct")
                add_user_points(user, ans, 2)

            # Check the total goals scored or the goal difference is correct (can't have both, or the prediction would be correct).
            elif ((user_total_goals == actual_total_goals) or (user_goal_difference == actual_goal_difference)):
                add_user_points(user, ans, 1)


# Helper method to add to user's total points.
def add_user_points(user, answer, pts):
    # Add points to user's total.
    user.profile.points = F('points') + pts
    user.save()
    user.refresh_from_db()
    
    # Update answer entry so points for this fixture aren't given to the user in the future.
    answer.points_added = answer.POINTS_ADDED
    answer.save()
    answer.refresh_from_db()

# Helper that determines if the outcome of a fixture is the same as it was previously, or not
def same_result(fixture1, fixture2):
    if fixture1.result_available() and fixture2.result_available():
        if fixture1.get_winner() == fixture2.get_winner():
            return True
        if fixture1.is_draw() and fixture2.is_draw():
            return True
    return False
