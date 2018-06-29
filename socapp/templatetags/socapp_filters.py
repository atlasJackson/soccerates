from django import template
from django.utils import timezone
import datetime, re

register = template.Library()

# Filter for adding a css class to a Form field.
@register.filter(name="add_class")
def add_class(field, css):
    return field.as_widget(attrs={"class": css})

# Adjust the stage string for display.
@register.filter(name="display_stage_heading")
def display_stage_heading(stage):
    return (" ").join(re.findall(r"[A-Za-z0-9\-]+", stage.upper()))

#
@register.filter(name="disable_input")
def disable_input(field):
    return field.as_widget(attrs={"disabled": True})

@register.filter(name="editable")
def editable(fixture):
    # Allow a fixture to be edited up to 15 mins before kickoff
    cutoff_time = fixture.match_date - datetime.timedelta(minutes=75)
    return timezone.now() < cutoff_time

# Filter for adding an id to a Form field.
@register.filter(name="add_id")
def add_id(field, name):
    return field.as_widget(attrs={"id": name})

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
@register.filter(name="getDistinctTeams")
def getDistinctTeams(fixtures):
    teams = []
    for fixture in fixtures:
        if fixture.team1 not in teams:
            teams.append(fixture.team1)
        if fixture.team2 not in teams:
            teams.append(fixture.team2)
    return teams

# Returns distinct set of teams for the queryset of fixtures passed in
@register.filter(name="getDistinctTeamsOrderedByPoints")
def getDistinctTeamsOrderedByPoints(fixtures):
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

# Returns the result of the fixture associated with the given fixture.
@register.filter(name="get_result")
def get_result(answer):
    if answer.fixture.has_extra_time: 
        return "Result: {} {}-{} {} *AET".format(
            answer.fixture.team1.name, answer.fixture.team1_goals, answer.fixture.team2_goals, answer.fixture.team2.name)
    else:
        return "Result: {} {}-{} {}".format(
            answer.fixture.team1.name, answer.fixture.team1_goals, answer.fixture.team2_goals, answer.fixture.team2.name)

# Returns the match date of the fixture associated with the given answer.
@register.filter(name="get_match_date")
def get_match_date(answer):
    return "Fixture will be played on {}".format(answer.fixture.match_date)

@register.filter(name="split_users")
def split_users(users):
    if len(users) <= 5:
        return ', '.join([str(u) for u in users])
    else:
        return "{} users".format(len(users))