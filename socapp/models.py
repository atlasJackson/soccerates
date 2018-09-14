from django.conf import settings
from django.template.defaultfilters import slugify

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F, When, Case, Value, Sum
from django.utils import timezone

import socapp.utils as utils

class Team(models.Model):
    group_names = ["A","B","C","D","E","F","G","H"]
    CHOICES = tuple((g, g) for g in group_names)

    name = models.CharField(max_length=32, unique=True)
    short_code = models.CharField(max_length=4)
    group = models.CharField(max_length=1, choices=CHOICES)
    flag = models.ImageField(blank=True)
    
    # For all games (group + knockout)
    games_played = models.IntegerField(default=0)
    games_won = models.IntegerField(default=0)
    games_drawn = models.IntegerField(default=0)
    games_lost = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    
    # For group games only
    group_won = models.IntegerField(default=0)
    group_drawn = models.IntegerField(default=0)
    group_lost = models.IntegerField(default=0)
    group_goals_for = models.IntegerField(default=0)
    group_goals_against = models.IntegerField(default=0)

    @property
    def points(self):
        return (3 * self.group_won) + self.group_drawn

    @property
    def goal_difference(self):
        return self.group_goals_for - self.group_goals_against
    
    #################################
    ### MODEL METHODS
    #################################
    def save(self, *args, **kwargs):
        if not self.group in self.group_names:
            raise ValidationError("Invalid group name")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def __eq__(self, other_team):
        return type(other_team) is Team and self.name == other_team.name


    #################################
    ### HELPER METHODS
    #################################

    # Returns the team instance's fixtures
    def get_fixtures(self):
        return Fixture.objects.filter(Q(team1=self) | Q(team2=self))
        #return self.team1_set.all() | self.team2_set.all()

    def fixtures_by_stage(self, stage):
        return self.get_fixtures().filter(stage=stage)

    def get_completed_fixtures(self):
        return self.get_fixtures().filter(status=Fixture.MATCH_STATUS_FINISHED)


################################################################################

# Tournament container model
class Tournament(models.Model):
    # LEAGUE = 1
    # KNOCKOUT = 2
    # GROUP_THEN_KNOCKOUT = 3
    # tournament_format_choices = (
    #     (LEAGUE, "League"),
    #     (KNOCKOUT, "Cup"),
    #     (GROUP_THEN_KNOCKOUT, "Group -> Knockout")
    # )

    name = models.CharField(max_length=128)
    #t_format = models.IntegerField(choices=tournament_format_choices, default=GROUP_THEN_KNOCKOUT)
    start_date = models.DateTimeField()
    winner = models.OneToOneField(Team, on_delete=models.SET_DEFAULT, default=None, null=True, blank=True)
    is_international = models.BooleanField(default=False)
    # best_user = models.OneToOneField(User)

    def __str__(self):
        return self.name

    # Get all the fixtures in the tournament, in date order (see Fixture Meta class)
    def get_fixtures(self):
        return Fixture.objects.filter(tournament=self.id)

    def all_fixtures_by_stage(self, stage):
        return self.get_fixtures().filter(stage=stage)
    
    def completed_fixtures(self):
        return self.get_fixtures().filter(status=Fixture.MATCH_STATUS_PLAYED)
    
    def unplayed_fixtures(self):
        return self.get_fixtures().filter(status=Fixture.MATCH_STATUS_NOT_PLAYED)

    def get_next_games(self, number=5):
        return self.unplayed_fixtures()[:number]

    def get_last_results(self, number=5):
        return self.completed_fixtures().reverse()[:number]

    # Returns users ordered by the points they've gained in this tournament
    def get_ranked_users(self):
        return self.userprofile_set.select_related('user').order_by('-points')

################################################################################

# Override Fixture's normal 'objects' Manager to automatically query for tournament and team info when a Fixture is loaded from the DB
class FixtureManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('tournament', 'team1', 'team2')

class Fixture(models.Model):

    """ TO DO: figure out best indexes for Fixture model. Tournament? """

    objects = FixtureManager() # Set objects to the above manager

    # Constants to determine if the match has been played, or not.
    # Could maybe extend this to add a status for matches that are happening?    
    MATCH_STATUS_NOT_PLAYED = 0
    MATCH_STATUS_PLAYED = 1

    MATCH_STATUS_CHOICES = (
        (MATCH_STATUS_NOT_PLAYED, "Match has not started"),
        (MATCH_STATUS_PLAYED, "Match has finished")
    )

    # Constants to determine if the Fixture is a group match, knockout, etc
    GROUP = 1
    ROUND_OF_16 = 2
    QUARTER_FINALS = 3
    SEMI_FINALS = 4
    FINAL = 5
    TPP = 6
    STAGE_CHOICES = (
        (GROUP, "Group"),
        (ROUND_OF_16, "Round of 16"),
        (QUARTER_FINALS, "Quarter Finals"),
        (SEMI_FINALS, "Semi Finals"),
        (FINAL, "Final"),
        (TPP, "Third Place Play-off")
    )
    
    # Specify related names, since there are 2 foreign keys to the same parent model.
    # This allows us to access the reverse relation, using team.team1_set or team.team2_set
    team1 = models.ForeignKey(Team, related_name="team1_set", on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name="team2_set", on_delete=models.CASCADE)
    tournament = models.ForeignKey("Tournament", on_delete=models.CASCADE)
    match_date = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(choices=MATCH_STATUS_CHOICES, default=MATCH_STATUS_NOT_PLAYED)

    # Could compare current-date to the match-date to determine whether or not the stage = PLAYED, or NOT PLAYED
    stage = models.IntegerField(choices=STAGE_CHOICES, default=GROUP)
    team1_goals = models.PositiveIntegerField(null=True, blank=True)
    team2_goals = models.PositiveIntegerField(null=True, blank=True)

    # For knockout rounds. Subject to change
    can_be_over_90 = models.BooleanField(default=False)
    has_extra_time = models.BooleanField(default=False)
    has_penalties = models.BooleanField(default=False)
    team1_penalties = models.PositiveIntegerField(null=True, blank=True)
    team2_penalties = models.PositiveIntegerField(null=True, blank=True)

    #################################
    ### HELPER METHODS
    #################################

    # Gets the group that the fixture is in
    def get_group(self):
        if self.stage == self.GROUP:
            return self.team1.group
        return None

    # Determines whether or not the match has occurred
    def result_available(self):
        return self.status == self.MATCH_STATUS_PLAYED

    # May need to alter this to accommodate extra time/penalties
    def is_draw(self):
        if self.result_available():
            return self.team1_goals == self.team2_goals
        return None
    
    # Finds the winner of this fixture.
    def get_winner(self):
        if self.result_available():
            if self.is_draw():
                return None
            return self.team1 if self.team1_goals > self.team2_goals else self.team2
        else:
            return None

    def get_loser(self):
        if self.result_available():
            if self.is_draw():
                return None
            return self.team1 if self.team1_goals < self.team2_goals else self.team2
        return None

    def has_result(self):
        return self.team1_goals is not None and self.team2_goals is not None

    def is_international(self):
        return self.tournament.is_international

    #################################
    ### STATIC METHODS
    #################################
    
    ## Move these to Tournament model ##
    
    @staticmethod
    def all_fixtures_by_stage(stage):
        return Fixture.objects.filter(stage=stage).order_by('match_date')
    
    @staticmethod
    def all_completed_fixtures():
        return Fixture.objects.filter(status=Fixture.MATCH_STATUS_PLAYED)
    
    @staticmethod
    def all_fixtures_by_group(group):
        if not group in Team.group_names:
            raise ValidationError("Invalid group name supplied")
        return Fixture.objects.filter((Q(team1__group=group) | Q(team2__group=group)) & Q(stage=Fixture.GROUP))
    
    # Gets all fixtures for the current day, or None if there are none
    @staticmethod
    def todays_fixtures():
        current_month, current_day = timezone.now().month, timezone.now().day   
        fixtures = Fixture.objects.filter(match_date__month=current_month, match_date__day=current_day)
        return fixtures or None


    #################################
    ### MODEL METHODS
    #################################

    def save(self, *args, **kwargs):
        self.full_clean()
        # Update status field based on whether or not there are goals for each team in the fixture
        if self.has_result():
            self.status = Fixture.MATCH_STATUS_PLAYED        
        if not self.has_result():
            self.status = Fixture.MATCH_STATUS_NOT_PLAYED

        # Update Team, User and Answer models based on the contents of the save.
        if self.pk is not None:
            prev_fixture = Fixture.objects.get(pk=self.pk)
            if not prev_fixture.has_result() and not self.has_result():
                pass
            else:
                if prev_fixture.has_result() and not self.has_result():
                    # Previously there was a result, now there's none: so remove the team/user data for the previous result
                    utils.remove_team_data(prev_fixture, self.team1)
                    utils.remove_team_data(prev_fixture, self.team2)
                    utils.update_user_pts(prev_fixture=prev_fixture, remove=True)
                elif not prev_fixture.has_result():
                    # Simply add the team data, since previously there was no result.
                    utils.add_team_data(self, self.team1)
                    utils.add_team_data(self, self.team2)
                    utils.update_user_pts(saved_fixture=self, add=True)
                else:
                    # Result already exists, so this save represents an update. Gather previous fixture data, and find differences
                    utils.update_team_data(prev_fixture, self, self.team1)
                    utils.update_team_data(prev_fixture, self, self.team2)
                    utils.update_user_pts(prev_fixture=prev_fixture, saved_fixture=self, update=True)
        else:
            if self.has_result():
                    utils.add_team_data(self, self.team1)
                    utils.add_team_data(self, self.team2)
                    utils.update_user_pts(saved_fixture=self, add=True)
        super().save(*args, **kwargs)

    def clean(self):
        # Prevent the same team being assigned to team1 and team2 (example: Brazil vs Brazil)
        if self.team1 == self.team2:
            raise ValidationError("Error assigning teams to this fixture. Teams must be distinct")
        # For group stage fixturres, ensure both teams are in the same group.
        if self.stage == self.GROUP and not self.team1.group == self.team2.group:
            raise ValidationError("Cannot add a group-stage match if both teams are not in the same group")
        # Ensure that the goals field cannot be set for one team, and None for the other
        if (self.team1_goals is not None and self.team2_goals is None) or (self.team1_goals is None and self.team2_goals is not None):
            raise ValidationError("Goals must be added for both teams in the fixture")

    # Returns valid string representation of the fixture
    def __str__(self):
        return "{} vs {}".format(self.team1, self.team2)

    # Defines whether or not two fixtures are equal
    def __eq__(self, other_fixture):
        if not type(other_fixture) is Fixture:
            return False
        if not self.match_date == other_fixture.match_date:
            return False
        this_teams = [self.team1, self.team2]
        other_teams = [other_fixture.team1, other_fixture.team2]
        for team in this_teams:
            if not team in other_teams:
                return False
        return True
    
    class Meta:
        ordering = ['match_date']



######################################################
#  Models for answers and leaderboards
######################################################

class Answer(models.Model):

    POINTS_NOT_ADDED = 0
    POINTS_ADDED = 1

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    team1_goals = models.PositiveIntegerField(default=0)
    team2_goals = models.PositiveIntegerField(default=0)
    
    has_extra_time = models.BooleanField(default=False)
    has_penalties = models.BooleanField(default=False)

    points_added = models.BooleanField(default=POINTS_NOT_ADDED)
    points = models.IntegerField(blank=True, null=True)


    def save(self, *args, **kwargs):
        if self.team1_goals is None or self.team2_goals is None:
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return "{}: {} {} - {} {}".format(
            self.user.username, 
            self.fixture.team1.name, 
            self.team1_goals, 
            self.team2_goals, 
            self.fixture.team2.name
        )

    @staticmethod
    def tournament_answers(tournament):
        return Answer.objects.select_related('user', 'fixture').filter(fixture__tournament=tournament)

    class Meta:
        # A user should only be able to submit one scoreline prediction per fixture
        unique_together = ('user', 'fixture')


class Leaderboard(models.Model):
    IN_PROGRESS = 0
    FINISHED = 1

    PUBLIC = 0
    PRIVATE = 1

    ACCESS_CHOICES = (
        (PUBLIC, "Public"),
        (PRIVATE, "Private")
    )

    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(unique=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    capacity = models.PositiveIntegerField(default=10) # Max number of users allowed.
    password = models.CharField(max_length=128, blank=True)

    is_private = models.BooleanField(choices=ACCESS_CHOICES, default=PUBLIC)
    is_finished = models.BooleanField(default=IN_PROGRESS) # Is the tournament finished: can calculate the leaderboard's winner if so

    ### Include competition for future use.

    WC_2018 = 0
    CL_201819 = 1
    
    COMP_CHOICES = (
        (WC_2018, "FIFA World Cup 2018"),
        (CL_201819, "UEFA Champions League 2018-19"),
    )

    competition = models.IntegerField(choices=COMP_CHOICES, default=WC_2018)

    #################################
    ### MODEL METHODS
    #################################
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Leaderboard, self).save(*args, **kwargs)



###############################
# !!!IGNORE FOR NOW

#
# class ScorelineAnswer(Answer):
#     team1_goals = models.IntegerField()
#     team2_goals = models.IntegerField()

#     def __str__(self):
#         return "{} predicts: {} {} - {} {}".format(
#             self.user.username, 
#             self.fixture.team1.name, 
#             self.team1_goals, 
#             self.team2_goals, 
#             self.fixture.team2.name
#         )
    

# class TextAnswer(Answer):
#     question = models.ForeignKey(TextQuestion, on_delete=models.CASCADE)
#     answer = models.CharField(max_length=56)

#     def __str__(self):
#         return "Q: {}. A: {}".format(self.question.text, self.answer)

# class Group(models.Model):

#     group_names = ["A","B","C","D","E","F","G","H"]
#     CHOICES = tuple((g, g) for g in group_names)
    
#     name = models.CharField(max_length=1, choices=CHOICES, unique=True)
    
#     #################################
#     ### MODEL METHODS
#     #################################

#     def save(self, *args, **kwargs):
#         if not self.name in self.group_names:
#             raise ValidationError("Invalid group name")
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return "Group {}".format(self.name)

#     def __eq__(self, other_group):
#         return type(other_group) is Group and self.name == other_group.name

#     #################################
#     ### HELPER METHODS
#     #################################

#     def get_fixtures(self):
#         return Fixture.objects.filter(team1__group__name=self.name, stage=Fixture.GROUP).order_by('match_date')
    
#     def get_teams(self):
#         return Team.objects.filter(group=self.id)

################################################################################

# Models for questions/answers

# class TextQuestion(models.Model):
#     # SCORELINE = 1
#     # USER_INPUT = 2

#     # QUESTION_TYPES = (
#     #     (SCORELINE, "Scoreline"),
#     #     (USER_INPUT, "User Input")
#     # )

#     text = models.CharField(max_length=64, default="Choose a result")
#     # type

#     def __str__(self):
#         return self.text