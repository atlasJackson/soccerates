from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from . import settings

urlpatterns = [
    path('', include("socapp.urls")),
    path('admin/', admin.site.urls),
]
