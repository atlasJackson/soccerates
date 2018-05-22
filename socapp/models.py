from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Team(models.Model):
    group_names = ["A","B","C","D","E","F","G","H"]
    CHOICES = tuple((g, g) for g in group_names)

    name = models.CharField(max_length=32, unique=True)
    country_code = models.CharField(max_length=4)
    group = models.CharField(max_length=1, choices=CHOICES)
    flag = models.ImageField(blank=True)
    
    games_won = models.IntegerField(default=0)
    games_drawn = models.IntegerField(default=0)
    games_lost = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)

    @property
    def points(self):
        return (3 * self.games_won) + self.games_drawn
    
    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against
    
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
        return Fixture.objects.select_related('team1', 'team2').filter(Q(team1=self.id) | Q(team2=self.id))
        #return self.team1_set.all() | self.team2_set.all()


################################################################################

# Potentially include details of whether it's a group match, or later... add penalties/extra time to the model (or result model)?
class Fixture(models.Model):
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
    LAST_16 = 2
    QUARTER_FINALS = 3
    SEMI_FINALS = 4
    FINAL = 5
    STAGE_CHOICES = (
        (GROUP, "Group"),
        (LAST_16, "Round of 16"),
        (QUARTER_FINALS, "Quarter Finals"),
        (SEMI_FINALS, "Semi Finals"),
        (FINAL, "Final")
    )
    
    # Specify related names, since there are 2 foreign keys to the same parent model.
    # This allows us to access the reverse relation, using team.team1_set or team.team2_set
    team1 = models.ForeignKey(Team, related_name="team1_set", on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name="team2_set", on_delete=models.CASCADE)
    match_date = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(choices=MATCH_STATUS_CHOICES, default=MATCH_STATUS_NOT_PLAYED)

    # Could compare current-date to the match-date to determine whether or not the stage = PLAYED, or NOT PLAYED
    stage = models.IntegerField(choices=STAGE_CHOICES, default=GROUP)
    team1_goals = models.PositiveIntegerField(null=True, blank=True)
    team2_goals = models.PositiveIntegerField(null=True, blank=True)

    # For knockout rounds. Subject to change
    has_extra_time = models.BooleanField(default=False)
    has_penalties = models.BooleanField(default=False)

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

    #################################
    ### STATIC METHODS
    #################################

    @staticmethod
    def all_fixtures_by_date():
        return Fixture.objects.select_related('team1', 'team2').order_by('match_date')
    
    @staticmethod
    def all_fixtures_by_stage(stage):
        return Fixture.objects.select_related('team1','team2').filter(stage=stage).order_by('match_date')
    
    @staticmethod
    def all_completed_fixtures():
        return Fixture.objects.select_related('team1','team2').filter(status=Fixture.MATCH_STATUS_PLAYED)
    
    @staticmethod
    def all_fixtures_by_group(group):
        if not group in Team.group_names:
            raise ValidationError("Invalid group name supplied")
        return Fixture.objects.select_related('team1', 'team2') \
            .filter((Q(team1__group=group) | Q(team2__group=group)) & Q(stage=Fixture.GROUP))


    #################################
    ### MODEL METHODS
    #################################

    def save(self, *args, **kwargs):
        # Prevent the same team being assigned to team1 and team2 (example: Brazil vs Brazil)
        if self.team1 == self.team2:
            raise ValidationError("Error assigning teams to this fixture. Teams must be distinct")
        # For group stage fixturres, ensure both teams are in the same group.
        if self.stage == self.GROUP and not self.team1.group == self.team2.group:
            raise ValidationError("Cannot add a group-stage match if both teams are not in the same group")
        super().save(*args, **kwargs)

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

""" Models for users, their answers, and leaderboards """

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    points = models.IntegerField(default=0) # Hold the points for the user

    def get_predictions(self):
        return Answer.objects.select_related('fixture', 'user').filter(user=self.user)

class Answer(models.Model):
    POINTS_NOT_ADDED = 0
    POINTS_ADDED = 1

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    team1_goals = models.PositiveIntegerField(default=0)
    team2_goals = models.PositiveIntegerField(default=0)

    # For this answer, have the points been added to the user model?
    # If not, and the game has been played, we should calculate the points accumulated for the game, and add them to the user model.
    # Then set this attribute to True
    points_added = models.BooleanField(default=POINTS_NOT_ADDED)


    def save(self, *args, **kwargs):
        if self.team1_goals is None:
            self.team1_goals = 0
        if self.team2_goals is None:
            self.team2_goals = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} predicts: {} {} - {} {}".format(
            self.user.username, 
            self.fixture.team1.name, 
            self.team1_goals, 
            self.team2_goals, 
            self.fixture.team2.name
        )
    
    class Meta:
        # A user should only be able to submit one scoreline prediction per fixture
        unique_together = ('user', 'fixture')

class Leaderboard(models.Model):
    IN_PROGRESS = 0
    FINISHED = 1

    name = models.CharField(max_length=64, unique=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    is_finished = models.BooleanField(default=IN_PROGRESS) # Is the tournament finished: can calculate the leaderboard's winner if so

    """ Model methods """
    def __str__(self):
        return self.name

###############################
# !!!IGNORE FOR NOW

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