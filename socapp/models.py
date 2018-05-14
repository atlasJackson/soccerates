from django.core.exceptions import ValidationError
from django.db import models

class Group(models.Model):
    group_names = ["A","B","C","D","E","F","G","H"]
    CHOICES = tuple((g, g) for g in group_names)
    
    name = models.CharField(max_length=1, choices=CHOICES, unique=True)

    def get_fixtures(self):
        return Fixture.objects.filter(team1__group__name=self.name, stage=Fixture.GROUP).order_by('match_date')
    
    def get_teams(self):
        return Team.objects.filter(group=self.id)

    def save(self, *args, **kwargs):
        if not self.name in self.group_names:
            raise ValidationError("Invalid group name")
        super().save(*args, **kwargs)

    def __str__(self):
        return "Group {}".format(self.name)

    def __eq__(self, other_group):
        return type(other_group) is Group and self.name == other_group.name

class Team(models.Model):
    name = models.CharField(max_length=32, unique=True)
    country_code = models.CharField(max_length=4) # Not required, could remove.
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    #flag = models.ImageField()

    def __str__(self):
        return self.name

    def __eq__(self, other_team):
        return type(other_team) is Team and self.name == other_team.name

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
    
    team1 = models.ForeignKey(Team, related_name="team1", on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name="team2", on_delete=models.CASCADE)
    match_date = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(choices=MATCH_STATUS_CHOICES, default=MATCH_STATUS_NOT_PLAYED)

    # Could compare current-date to the match-date to determine whether or not the stage = PLAYED, or NOT PLAYED
    stage = models.IntegerField(choices=STAGE_CHOICES, default=GROUP)
    team1_goals = models.PositiveIntegerField(null=True, blank=True)
    team2_goals = models.PositiveIntegerField(null=True, blank=True)

    
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

    @staticmethod
    def all_fixtures_by_date():
        return Fixture.objects.order_by('match_date')
    
    @staticmethod
    def all_fixtures_by_stage(stage):
        return Fixture.objects.filter(stage=stage).order_by('match_date')
    
    @staticmethod
    def all_completed_fixtures():
        return Fixture.objects.filter(status=Fixture.MATCH_STATUS_PLAYED)


    ### OVERRIDES ###
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