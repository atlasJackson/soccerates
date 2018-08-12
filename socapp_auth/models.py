from django.conf import settings
from django.db import models
from socapp.models import Answer

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    picture = models.ImageField(upload_to='profile/profile_images', blank=True)
    points = models.IntegerField(default=0) # Hold the points for the user

    def get_predictions(self):
        return Answer.objects.select_related('fixture', 'user', 'fixture__team1', 'fixture__team2') \
            .filter(user=self.user)

    def __str__(self):
        return self.user.username
        