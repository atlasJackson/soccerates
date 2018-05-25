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
    
    # Enumerates over the ranked sublists, finds which one the user is in, and returns the ranking
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