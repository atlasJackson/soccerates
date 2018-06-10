from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('test/', views.test, name='test'),    

    path('profile/', views.user_profile, name='profile'),
    path('login/', auth_views.LoginView.as_view(template_name="login.html"), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register', views.RegistrationView.as_view(), name='register'),

    path('answer_form/', views.answer_form, name='answer_form'),
    path('worldcup/schedule/', views.world_cup_schedule, name='wc_schedule'),

    path('leaderboards/', views.leaderboards, name='leaderboards'),
    path('leaderboards/<slug:leaderboard>/', views.show_leaderboard, name='show_leaderboard'),
    path('leaderboards/<slug:leaderboard>/join_leaderboard/', views.join_leaderboard, name='join_leaderboard'),
    path('leaderboards/<slug:leaderboard>/leave_leaderboard/', views.leave_leaderboard, name='leave_leaderboard'),
    
    path('forums/', views.forums, name='forums'),
]

# AJAX URLS
urlpatterns += [
    path('ajax/leaderboards/get_page', views.paginate_leaderboards, name='paginate_leaderboard'),
    path('ajax/leaderboards/search', views.search_leaderboards, name='search_leaderboard')
]