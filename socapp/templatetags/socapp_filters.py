from django import template

register = template.Library()

# Filter for adding a css class to a Form field.
@register.filter(name="add_class")
def add_class(field, css):
    return field.as_widget(attrs={"class": css})

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