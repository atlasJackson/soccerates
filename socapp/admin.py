from django.contrib import admin
from .models import *

# Register your models here.
#admin.site.register(Group)
admin.site.register(UserProfile)
admin.site.register(Leaderboard)

admin.site.register(Team)
admin.site.register(Fixture)
admin.site.register(Answer)