from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    path('answer_form', views.answer_form, name='answer_form'),
    path('profile', views.user_profile, name='profile'),
    path('worldcup/schedule', views.world_cup_schedule, name='wc_schedule'),

    path('login/', auth_views.LoginView.as_view(template_name="login.html"), name='login'),
    path('logout', auth_views.LogoutView.as_view(), name='logout'),
    path('register', views.RegistrationView.as_view(), name='register')
]
