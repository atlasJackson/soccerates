from django import template

register = template.Library()

# Filter for adding a css class to a Form field.
@register.filter(name="add_class")
def add_class(field, css):
    return field.as_widget(attrs={"class": css})

# Return first team in the list. Used in template to predict scores.
@register.filter(name='getGroup')
def getGroup(list, i):
    return list[i].get_group()

# Return first team in the list. Used in template to predict scores.
@register.filter(name='getTeamOne')
def getTeamOne(list, i):
    return list[i].team1

# Return second team in the list. Used in template to predict scores.
@register.filter(name='getTeamTwo')
def getTeamTwo(list, i):
    return list[i].team2

# Return date in the list. Used in template to predict scores.
@register.filter(name='getMatchDate')
def getMatchDate(list, i):
    return list[i].match_date

# Return date in the list. Used in template to predict scores.
@register.filter(name='getGroupGamesPlayed')
def getGroupGamesPlayed(team):
    return (team.group_won + team.group_drawn + team.group_lost)

# Returns distinct set of teams for the queryset of fixtures passed in
@register.filter(name="getDistinctTeamsOrderedByPoints")
def getDistinctTeamsOrderedByPoints(fixtures):
    print(fixtures)
    teams = []
    while len(teams) < 4:
        for fixture in fixtures:
            if fixture.team1 not in teams:
                teams.append(fixture.team1)
            if fixture.team2 not in teams:
                teams.append(fixture.team2)
    return sorted(teams, key=lambda team: (team.points, team.goal_difference, team.group_goals_for), reverse=True)

# Returns the rank of the user in the leaderboard.
@register.filter(name="get_user_leaderboard_position")
def get_user_leaderboard_position(leaderboard, user):

    # Sort the leaderboard by users points in descending order.
    users_in_leaderboard = [(user.profile.points, user) for user in leaderboard.users.all()]
    sorted_leaderboard = sorted(users_in_leaderboard, key=lambda u: u[0], reverse=True)

    # Get the index (rank) of the user.
    for index,u in enumerate(sorted_leaderboard):
        if u[1].username == str(user):
            return (index + 1)

    # This should never be reached.
    return "-"

# Returns number of free spaces in the leaderboard.
@register.filter(name="get_free_spaces")
def get_free_spaces(leaderboard):

    return leaderboard.capacity - leaderboard.users.count()

# Returns points for a given fixture.
@register.filter(name="get_answer_points")
def get_answer_points(answer):
    """
    Takes an answer, and calculates the points to be given for the user who added the Answer
    """
    fixture = answer.fixture
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