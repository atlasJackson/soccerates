"""
Utility methods for common/complex tasks
"""

from .models import *
from django.utils import timezone

# Returns the next games to be played, the number of which can be specified, but which defaults to 3
def get_next_games(number=3):
    cur_date = timezone.now()
    # Since the Fixture model's default ordering is by match_date, we can just take a slice of the query results
    fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_NOT_PLAYED)[:number]
    for fixture in fixtures:
        assert cur_date < fixture.match_date # If this fails, something has gone wrong.
    return fixtures

# Returns the last games that were played, the number of which can be specified, but which defaults to 3.
def get_last_results(number=3):
    cur_date = timezone.now()
    fixtures = Fixture.objects.select_related('team1', 'team2') \
        .filter(status=Fixture.MATCH_STATUS_PLAYED).reverse()[:number]
    for fixture in fixtures:
        assert cur_date > fixture.match_date
    return fixtures