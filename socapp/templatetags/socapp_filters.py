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
    return (team.games_won + team.games_drawn + team.games_lost)

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
    return sorted(teams, key=lambda team: team.points, reverse=True)