from django.core.exceptions import ValidationError
from django.db import models

class Group(models.Model):
    group_names = ["A","B","C","D","E","F","G","H"]
    CHOICES = tuple((g, g) for g in group_names)
    
    name = models.CharField(max_length=1, choices=CHOICES)

    def get_fixtures(self):
        # return all fixtures in the group. Implement for group-stage matches only.
        pass

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
    # Could maybe extend this to add a status for matches that are happening?    
    MATCH_STATUS_NOT_STARTED = 0
    MATCH_STATUS_FINISHED = 1

    MATCH_STATUS_CHOICES = (
        (MATCH_STATUS_NOT_STARTED, "Match has not started"),
        (MATCH_STATUS_FINISHED, "Match has finished")
    )

    team1 = models.ForeignKey(Team, related_name="team1", on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name="team2", on_delete=models.CASCADE)
    match_date = models.DateTimeField(null=True, blank=True)
    status = models.BooleanField(choices=MATCH_STATUS_CHOICES, default=MATCH_STATUS_NOT_STARTED)

    # For the result: keep here, or extract to its own table?
    team1_goals = models.PositiveIntegerField(default=0)
    team2_goals = models.PositiveIntegerField(default=0)

    # Gets the group that the fixture is in
    def get_group(self):
        # if stage == group
        if self.team1.group == self.team2.group:
            return self.team1.group

    # Returns whether or not the match has occurred
    def result_available(self):
        return self.status == self.MATCH_STATUS_FINISHED

    # May need to alter this to accommodate extra time/penalties
    def is_draw(self):
        if self.result_available():
            return self.team1_goals == self.team2_goals
        # raise exception?
    
    # Finds the winner.
    def get_winner(self):
        if self.result_available():
            if self.is_draw():
                return
            return self.team1 if self.team1_goals > self.team2_goals else self.team2
        else:
            return
        

    def __str__(self):
        return "{} vs {}".format(self.team1, self.team2)