from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import IntegrityError
import random, string, sys

from socapp.models import *

class Command(BaseCommand):
    help = 'Loads fake data for testing'

    results = [
        { 'team1_goals': 2, 'team2_goals': 1 }, 
        { 'team1_goals': 0, 'team2_goals': 0 },
        { 'team1_goals': 4, 'team2_goals': 3 },
        { 'team1_goals': 2, 'team2_goals': 2 }, 
        { 'team1_goals': 1, 'team2_goals': 3 }, 
        { 'team1_goals': 5, 'team2_goals': 1 }  
    ]

    created_user_predictions = [
        { 'team1_goals': 1, 'team2_goals': 1 }, 
        { 'team1_goals': 0, 'team2_goals': 2 },
        { 'team1_goals': 2, 'team2_goals': 3 },
        { 'team1_goals': 1, 'team2_goals': 0 }, 
        { 'team1_goals': 0, 'team2_goals': 2 }, 
        { 'team1_goals': 2, 'team2_goals': 1 }  
    ]

    user1_predictions = [
        { 'team1_goals': 2, 'team2_goals': 1 }, 
        { 'team1_goals': 2, 'team2_goals': 2 }, 
        { 'team1_goals': 0, 'team2_goals': 3 }, 
        { 'team1_goals': 1, 'team2_goals': 3 }, 
        { 'team1_goals': 2, 'team2_goals': 4 }, 
        { 'team1_goals': 1, 'team2_goals': 0 } 
    ]

    user2_predictions = [
        { 'team1_goals': 2, 'team2_goals': 2 }, 
        { 'team1_goals': 2, 'team2_goals': 0 }, 
        { 'team1_goals': 2, 'team2_goals': 1 }, 
        { 'team1_goals': 1, 'team2_goals': 0 }, 
        { 'team1_goals': 1, 'team2_goals': 3 }, 
        { 'team1_goals': 6, 'team2_goals': 0 }
    ]

    user3_predictions = [
        { 'team1_goals': 2, 'team2_goals': 1 },
        { 'team1_goals': 0, 'team2_goals': 0 },
        { 'team1_goals': 4, 'team2_goals': 3 },
        { 'team1_goals': 2, 'team2_goals': 2 },
        { 'team1_goals': 1, 'team2_goals': 3 },
        { 'team1_goals': 5, 'team2_goals': 1 } 
    ]

    users = []
    prediction_list = [created_user_predictions, user1_predictions, user2_predictions, user3_predictions]

    # This method is executed when the management command is run.
    def handle(self, *args, **kwargs):
        """
        1. Create 3 users
        2. Add their answers for Group A fixtures
        3. Add the users to a leaderboard
        4. Add results for the associated fixtures
        """
        print("Working...")
        self.reset_fixtures()
        self.create_users(kwargs['username'], kwargs['password'])
        for user, predictions in zip(self.users, self.prediction_list):
            self.add_predictions(user, predictions)

        board = Leaderboard.objects.get_or_create(name="Test Board", capacity=10)[0]
        for user in self.users:
            board.users.add(user)
        
        self.add_results()
    
    # Specifies the username and password of a user to be created: allows us to login as that user and see the results.
    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('password')

    # Add a result for each fixture in Group A
    def add_results(self):
        fixtures = Fixture.all_fixtures_by_group("A")
        assert fixtures.count() == len(self.results)
        for fixture, result in zip(fixtures, self.results):
            fixture.team1_goals = result['team1_goals']
            fixture.team2_goals = result['team2_goals']
            fixture.save()
            fixture.refresh_from_db()

    # Create an answer for each fixture, for the user generated in the setUp method.
    def add_predictions(self, user, predictions):
        fixtures = Fixture.all_fixtures_by_group("A")
        assert fixtures.count() == len(predictions)
        for fixture, prediction in zip(fixtures, predictions):
            a = Answer(fixture=fixture, user=user)
            a.team1_goals = prediction['team1_goals']
            a.team2_goals = prediction['team2_goals']
            a.save() 

    # Create 3 users
    def create_users(self, username, pw):
        existing_users = get_user_model().objects.filter(email__endswith="pytest.com")
        if existing_users.exists():
            existing_users.delete()

        try:
            u = get_user_model().objects.create_user(username=username, password=pw, email=self.str_generator() + "@pytest.com")
            self.users.append(u)
        except IntegrityError:
            print("User with that name already exists. Aborting!")
            sys.exit()

        for i in range(3):
            u = get_user_model().objects.create_user(
                username=self.str_generator(), \
                password="test", \
                email=self.str_generator() + "@pytest.com")
            self.users.append(u)

    def reset_fixtures(self):
        for f in Fixture.all_fixtures_by_group("A"):
            f.team1_goals = f.team2_goals = None
            f.save()

    def str_generator(self):
        return ''.join(random.choices(string.ascii_lowercase, k=5))