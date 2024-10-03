from django.urls import path, re_path
from . import views
from .views import  song_details

urlpatterns = [
    path('', views.home_view, name='home_view'),
    path('login/', views.login_register_view, name='login_register'),
    path('logout/', views.logout_view, name='logout'),
    path('chat/', views.chat_view, name='chat_view'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('song/<int:song_id>/', song_details, name='song_details'),
    path('add-to-favorites/', views.add_to_favorites, name='add_to_favorites'),
    path('add-to-playlist/', views.add_to_playlist, name='add_to_playlist'),
    path('recommend-songs/', views.recommend_songs_view, name='recommend_songs'),
    path('playlists/', views.playlist_list, name='playlist_list'),
    path('playlists/create/', views.create_playlist, name='create_playlist'),
    path('playlists/update/<int:playlist_id>/', views.update_playlist, name='update_playlist'),
    path('playlists/delete/<int:playlist_id>/', views.delete_playlist, name='delete_playlist'),
    path('favorites/remove/<int:favorite_id>/', views.remove_favorite, name='remove_favorite'),
    path('songs/', views.song_list_view, name='song_list'),
    path('playlist/<int:playlist_id>/', views.playlist_detail_view, name='playlist_detail'),
    path('playlist_song/<int:playlist_song_id>/remove/', views.remove_from_playlist, name='remove_from_playlist'),
    path('visualizations/', views.visualizations, name='visualizations'),
    path('reports/', views.reports_generation_view, name='reports'),
    

]
