from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(SongRecommendation)
class SongRecommendationAdmin(admin.ModelAdmin):
    list_display = ('name', 'artist', 'user', 'created_at')
    search_fields = ('name', 'artist')
    
admin.site.register(Playlist)
admin.site.register(PlaylistSong)
admin.site.register(Favorite)