from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('test/', views.test, name='test'),    

    path('profile', views.user_profile, name='profile'),
    path('users/<slug:username>/profile', views.user_profile, name='other_user_profile'),

    path('score_predictions/', views.answer_form, name='answer_form'),
    path('score_predictions/points_system/', views.points_system, name='points_system'),
    path('score_predictions/<slug:stage>/', views.answer_form_selected, name='answer_form_selected'),
    
    path('worldcup/schedule/', views.world_cup_schedule, name='wc_schedule'),

    path('leaderboards/', views.leaderboards, name='leaderboards'),
    path('leaderboards/global_leaderboard/', views.global_leaderboard, name='global_leaderboard'),
    path('leaderboards/friends_leaderboard/', views.friends_leaderboard, name='friends_leaderboard'),
    path('leaderboards/<slug:leaderboard>/', views.show_leaderboard, name='show_leaderboard'),
    path('leaderboards/<slug:leaderboard>/join_leaderboard/', views.join_leaderboard, name='join_leaderboard'),
    path('leaderboards/<slug:leaderboard>/leave_leaderboard/', views.leave_leaderboard, name='leave_leaderboard'),
    
    path('forums/', views.forums, name='forums'),
]

# AJAX URLS
urlpatterns += [
    path('ajax/leaderboards/get_page', views.paginate_leaderboards, name='paginate_leaderboard'),
    path('ajax/leaderboards/search', views.search_leaderboards, name='search_leaderboard'),
    path('ajax/profile/get_predictions', views.user_profile, name='user_predictions')
]