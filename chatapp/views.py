from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import *
from django.contrib import messages



def dashboard_view(request):
    user = request.user
    
    # Fetch the 5 most recent song recommendations
    recent_songs = SongRecommendation.objects.filter(user=user).order_by('-created_at')[:5]

    # Fetch the 5 most recent favorites
    recent_favorites = Favorite.objects.filter(user=user).order_by('-added_at')[:5]
    
    # Fetch 2 recommended playlists for the user
    recommended_playlists = Playlist.objects.filter(user=user).order_by('-created_at')[:2]

    context = {
        'user': user,
        'recent_songs': recent_songs,
        'recent_favorites': recent_favorites,
        'recommended_playlists': recommended_playlists,
    }

    return render(request, 'dashboard.html', context)


@login_required
def song_details(request, song_id):
    song = SongRecommendation.objects.get(id=song_id)
    is_favorite = Favorite.objects.filter(user=request.user, song=song).exists()
    return render(request, 'song_details.html', {'song': song, 'is_favorite': is_favorite})


def login_register_view(request):
    error_message = None  # To store error messages

    if request.method == 'POST':
        # Check which form was submitted using 'tab'
        if 'login' in request.POST:
            # Handle login form
            username = request.POST.get('user')
            password = request.POST.get('pass')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                error_message = "Invalid username or password."
        
        elif 'register' in request.POST:
            # Handle registration form
            username = request.POST.get('user')
            password = request.POST.get('pass')
            repeat_password = request.POST.get('repeat_pass')
            email = request.POST.get('email')
            
            # Check if passwords match
            if password != repeat_password:
                error_message = "Passwords do not match."
            else:
                # Check if the username or email already exists
                if User.objects.filter(username=username).exists():
                    error_message = "Username already taken."
                elif User.objects.filter(email=email).exists():
                    error_message = "Email already in use."
                else:
                    # Create a new user
                    user = User.objects.create_user(username=username, password=password, email=email)
                    login(request, user)
                    return redirect('dashboard')
    
    return render(request, 'login.html', {'error_message': error_message})



def home_view(request):
    # This view is protected, so it requires the user to be logged in
    return render(request, 'home.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login_register')


from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
import google.generativeai as genai
import pylast
import json
import re

# Configure the Google Generative AI API
genai.configure(api_key=settings.GENAI_API_KEY)

# Configure the Last.fm API
API_KEY = settings.API_KEY
API_SECRET = settings.API_SECRET
USERNAME = 'dasjhjhads'
PASSWORD_HASH = pylast.md5(settings.PASSWORD)

network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET, username=USERNAME, password_hash=PASSWORD_HASH)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",  # Ensure the response is in JSON format
}
aimodel = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="suggest 5 popular appropriate musics that resonate with the user's feelings in the format {\"suggestions\": [{\"Track\": \"track_name\", \"Artist\": \"artist_name\"}, ...]}",
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You are Tenor, an empathetic chatbot that suggests music based on the user's emotions. You ask engaging and thoughtful questions to understand how the user is feeling without directly asking for music recommendations, mood, or emotions. Through the conversation, you infer their emotional state and suggest 5 songs that resonate with their feelings in the format {\"suggestions\": [{\"Track\": \"track_name\", \"Artist\": \"artist_name\"}, ...]}",
)

@login_required
def chat_view(request):
    if 'conversation' not in request.session:
        request.session['conversation'] = []

    user_input = request.POST.get('user_input')
    song_recommendations = []

    if user_input:
        # Append user input to conversation
        request.session['conversation'].append({'role': 'user', 'parts': [user_input]})
        request.session.modified = True

        # Get model response
        try:
            convo = model.start_chat(history=request.session['conversation'])
            response = convo.send_message(user_input)

            # Parse the JSON response
            json_response = json.loads(response.text)
            music_suggestions = json_response.get('suggestions', [])
            
        except Exception as e:
            music_suggestions = []
            print(f"Error during model interaction: {e}")

        # Append model response to conversation
        request.session['conversation'].append({'role': 'model', 'parts': [response.text]})
        request.session.modified = True

        # Process music suggestions
        for suggestion in music_suggestions:
            try:
                track_name = suggestion.get('Track')
                artist_name = suggestion.get('Artist')

                if track_name and artist_name:
                    track = network.get_track(artist_name, track_name)
                    album = track.get_album()
                    album_cover = album.get_cover_image() if album else None

                    # Convert tags to strings
                    tags = track.get_top_tags()
                    tag_names = [str(tag.item) for tag in tags]

                    song_data = {
                        'name': track.title,
                        'artist': track.artist.name,
                        'url': track.get_url() + '?autostart',
                        'tags': tag_names,
                        'thumbnail': album_cover,
                        'description': track.get_wiki_content(),
                        'youtube_link': get_youtube_link(track)
                    }

                    # Create and save SongRecommendation
                    song_recommendation = SongRecommendation.objects.create(
                        user=request.user,
                        name=song_data['name'],
                        artist=song_data['artist'],
                        url=song_data['url'],
                        tags=", ".join(song_data['tags']),
                        thumbnail=song_data['thumbnail'],
                        description=song_data['description'],
                        youtube_link=song_data['youtube_link']
                    )

                    # Add the song recommendation along with its ID to the recommendations list
                    song_recommendations.append({
                        'id': song_recommendation.id,  # Save the ID for later use
                        **song_data
                    })

            except pylast.WSError as e:
                print(f"Error fetching track details: {e}")
                continue
            
    # Fetch all recommended songs for the logged-in user from the database
    song_recommendations = SongRecommendation.objects.filter(user=request.user).order_by('-created_at')

    # Fetch the logged-in user's playlists
    user_playlists = Playlist.objects.filter(user=request.user)

    # Render the response with the conversation and song recommendations
    return render(request, 'chat.html', {
        'conversation': request.session['conversation'],
        'username': request.user.username,
        'song_recommendations': song_recommendations,
        'playlists': user_playlists,
    })




def get_youtube_link(track):
    # Get YouTube link based on the track artist and title
    return f"https://www.youtube.com/results?search_query={track.artist.name}+{track.title}"

@login_required
def add_to_favorites(request):
    if request.method == 'POST':
        song_id = request.POST.get('song_id')
        redirect_url = request.POST.get('next', 'song_list')  # Get the redirect URL or default to 'song_list'
        song = SongRecommendation.objects.get(id=song_id)

        # Check if the song is already in favorites
        if not Favorite.objects.filter(user=request.user, song=song).exists():
            Favorite.objects.create(user=request.user, song=song)
            messages.success(request, f"Added '{song.name}' to your favorites.")
        else:
            messages.warning(request, f"'{song.name}' is already in your favorites.")

        return redirect(redirect_url)  # Redirect to the URL passed in the form

@login_required
def add_to_playlist(request):
    if request.method == 'POST':
        song_id = request.POST.get('song_id')
        playlist_id = request.POST.get('playlist_id')
        redirect_url = request.POST.get('next', 'song_list')  # Get redirect URL or default to 'song_list'

        song = SongRecommendation.objects.get(id=song_id)
        playlist = Playlist.objects.get(id=playlist_id)

        # Ensure the song is not already in the playlist
        if not PlaylistSong.objects.filter(playlist=playlist, song=song).exists():
            PlaylistSong.objects.create(playlist=playlist, song=song)
            messages.success(request, f"Added '{song.name}' to '{playlist.name}'.")
        else:
            messages.warning(request, f"'{song.name}' is already in '{playlist.name}'.")

        return redirect(redirect_url)  # Redirect back to the page where the form was submitted



    
@login_required
def recommend_songs_view(request):
    if 'conversation' not in request.session:
        request.session['conversation'] = []

    # Get user inputs for song recommendations
    scenario = request.POST.get('scenario')
    genre = request.POST.get('genre')
    artist = request.POST.get('artist')
    custom_field = request.POST.get('custom_field')
    song_recommendations = []

    if scenario or genre or artist or custom_field:
        user_input = f"Scenario: {scenario}, Genre: {genre}, Artist: {artist}, Custom: {custom_field}"
        
        # Append user input to conversation
        request.session['conversation'].append({'role': 'user', 'parts': [user_input]})
        request.session.modified = True

        # Get model response
        try:
            convo = aimodel.start_chat(history=request.session['conversation'])
            response = convo.send_message(user_input)

            # Parse the JSON response
            json_response = json.loads(response.text)
            music_suggestions = json_response.get('suggestions', [])
            
        except Exception as e:
            music_suggestions = []
            print(f"Error during model interaction: {e}")

        # Append model response to conversation
        request.session['conversation'].append({'role': 'model', 'parts': [response.text]})
        request.session.modified = True

        # Process music suggestions
        for suggestion in music_suggestions:
            try:
                track_name = suggestion.get('Track')
                artist_name = suggestion.get('Artist')

                if track_name and artist_name:
                    track = network.get_track(artist_name, track_name)
                    album = track.get_album()
                    album_cover = album.get_cover_image() if album else None

                    tags = track.get_top_tags()
                    tag_names = [str(tag.item) for tag in tags]

                    song_data = {
                        'name': track.title,
                        'artist': track.artist.name,
                        'url': track.get_url() + '?autostart',
                        'tags': tag_names,
                        'thumbnail': album_cover,
                        'description': track.get_wiki_content(),
                        'youtube_link': get_youtube_link(track)
                    }

                    song_recommendation = SongRecommendation.objects.create(
                        user=request.user,
                        name=song_data['name'],
                        artist=song_data['artist'],
                        url=song_data['url'],
                        tags=", ".join(song_data['tags']),
                        thumbnail=song_data['thumbnail'],
                        description=song_data['description'],
                        youtube_link=song_data['youtube_link']
                    )

                    song_recommendations.append({
                        'id': song_recommendation.id,
                        **song_data
                    })

            except pylast.WSError as e:
                print(f"Error fetching track details: {e}")
                continue

    # Fetch the last 5 recommended songs for the logged-in user from the database
    song_recommendations = SongRecommendation.objects.filter(user=request.user).order_by('-created_at')[:5]


    # Fetch the logged-in user's playlists
    user_playlists = Playlist.objects.filter(user=request.user)

    # Render the response with the conversation and song recommendations
    return render(request, 'recommend_songs.html', {
        'conversation': request.session['conversation'],
        'username': request.user.username,
        'song_recommendations': song_recommendations,
        'playlists': user_playlists,
    })


from django.shortcuts import render, redirect, get_object_or_404
from .models import Playlist
from .forms import PlaylistForm
@login_required
def playlist_list(request):
    playlists = Playlist.objects.filter(user=request.user)  # Assuming you have a user-based system
    return render(request, 'playlists.html', {'playlists': playlists})

@login_required
def create_playlist(request):
    if request.method == 'POST':
        form = PlaylistForm(request.POST, request.FILES)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.user = request.user  # Assuming a user model is involved
            playlist.save()
            return redirect('playlist_list')
    else:
        form = PlaylistForm()
    return render(request, 'create_playlist.html', {'form': form})

@login_required
def update_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    if request.method == 'POST':
        form = PlaylistForm(request.POST, request.FILES, instance=playlist)
        if form.is_valid():
            form.save()
            return redirect('playlist_list')
    else:
        form = PlaylistForm(instance=playlist)
    return render(request, 'edit_playlist.html', {'form': form})

@login_required
def delete_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    if request.method == 'POST':
        playlist.delete()
        return redirect('playlist_list')
    return render(request, 'delete_playlist.html', {'playlist': playlist})

@login_required
def favorites_view(request):
    # Fetch the user's favorite songs
    favorites = Favorite.objects.filter(user=request.user).select_related('song')
    return render(request, 'favorites.html', {'favorites': favorites})

@login_required
def remove_favorite(request, favorite_id):
    favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)
    favorite.delete()
    return redirect('favorites')

@login_required
def song_list_view(request):
    songs = SongRecommendation.objects.all()
    favorites = Favorite.objects.filter(user=request.user).values_list('song_id', flat=True)
    # Fetch the logged-in user's playlists
    user_playlists = Playlist.objects.filter(user=request.user)

    # Example: Playlist logic would be handled similarly (omitted for simplicity)
    return render(request, 'song_list.html', {'songs': songs, 'favorites': favorites, 'playlists': user_playlists,})




from django.shortcuts import render, get_object_or_404
from .models import Playlist, PlaylistSong

def playlist_detail_view(request, playlist_id):
    # Fetch the playlist and its associated songs
    playlist = get_object_or_404(Playlist, id=playlist_id)
    songs = PlaylistSong.objects.filter(playlist=playlist).select_related('song')
    
    context = {
        'playlist': playlist,
        'songs': songs
    }
    
    return render(request, 'playlist_songs.html', context)

def remove_from_playlist(request, playlist_song_id):
    playlist_song = get_object_or_404(PlaylistSong, id=playlist_song_id)
    playlist_id = playlist_song.playlist.id

    if request.method == 'POST':
        playlist_song.delete()
        return redirect('playlist_detail', playlist_id=playlist_id)

    return redirect('playlist_detail', playlist_id=playlist_id)




import json
from django.shortcuts import render
from django.db.models import Count
from .models import SongRecommendation, Playlist

def visualizations(request):
    # Top 5 artists by the number of songs
    artist_data = list(
        SongRecommendation.objects.values('artist')
        .annotate(count=Count('artist'))
        .order_by('-count')[:5]
    )

    # Playlists grouped by users
    playlist_data = list(
        Playlist.objects.values('user__username')
        .annotate(playlist_count=Count('id'))
        .order_by('-playlist_count')[:5]
    )

    # Prepare data as JSON
    context = {
        'artist_data': json.dumps(artist_data),  # Convert to JSON string
        'playlist_data': json.dumps(playlist_data)  # Convert to JSON string
    }

    return render(request, 'visualizations.html', context)

from django.db.models import Count
from .models import SongRecommendation, Playlist, PlaylistSong, Favorite
from django.utils import timezone
from datetime import timedelta

@login_required
def reports_generation_view(request):
    report_type = request.GET.get('report_type', 'overview')
    
    if report_type == 'overview':
        report_data = generate_overview_report(request.user)
    elif report_type == 'top_artists':
        report_data = generate_top_artists_report(request.user)
    elif report_type == 'playlist_analysis':
        report_data = generate_playlist_analysis_report(request.user)
    elif report_type == 'recent_activity':
        report_data = generate_recent_activity_report(request.user)
    else:
        report_data = {'error': 'Invalid report type'}

    context = {
        'report_type': report_type,
        'report_data': report_data,
    }

    return render(request, 'reports_generation.html', context)

def generate_overview_report(user):
    total_songs = SongRecommendation.objects.filter(user=user).count()
    total_playlists = Playlist.objects.filter(user=user).count()
    total_favorites = Favorite.objects.filter(user=user).count()

    return {
        'total_songs': total_songs,
        'total_playlists': total_playlists,
        'total_favorites': total_favorites,
    }

def generate_top_artists_report(user):
    top_artists = SongRecommendation.objects.filter(user=user) \
        .values('artist') \
        .annotate(count=Count('artist')) \
        .order_by('-count')[:10]

    return {'top_artists': list(top_artists)}

def generate_playlist_analysis_report(user):
    playlists = Playlist.objects.filter(user=user) \
        .annotate(song_count=Count('songs')) \
        .order_by('-song_count')

    return {'playlists': list(playlists.values('name', 'song_count'))}

def generate_recent_activity_report(user):
    last_month = timezone.now() - timedelta(days=30)
    recent_songs = SongRecommendation.objects.filter(user=user, created_at__gte=last_month) \
        .order_by('-created_at')[:10]
    recent_playlists = Playlist.objects.filter(user=user, created_at__gte=last_month) \
        .order_by('-created_at')[:5]
    recent_favorites = Favorite.objects.filter(user=user, added_at__gte=last_month) \
        .order_by('-added_at')[:10]

    return {
        'recent_songs': list(recent_songs.values('name', 'artist', 'created_at')),
        'recent_playlists': list(recent_playlists.values('name', 'created_at')),
        'recent_favorites': list(recent_favorites.values('song__name', 'song__artist', 'added_at')),
    }









