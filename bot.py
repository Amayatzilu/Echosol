import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

# Load environment variables (Ensure TOKEN is stored in Railway Variables or .env file)
TOKEN = os.getenv("TOKEN")

# Bot setup with command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configure YouTube downloader settings
cookies_path = "/app/cookies.txt"
cookie_data = os.getenv("YOUTUBE_COOKIES", "")

if cookie_data:
    with open(cookies_path, "w") as f:
        f.write(cookie_data)

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'False',
    'cookiefile': cookies_path,
    'postprocessors': [{  # Convert to MP3
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': '%(title)s.%(ext)s',  # Save with actual title as filename
    'noprogress': True,
    'nocheckcertificate': True,
    'geo_bypass': True,
    'quiet': True,
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
}

FFMPEG_OPTIONS = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

song_queue = []  # Queue for storing songs
playlists = {}  # Dictionary to store user playlists
volume_level = 1.0  # Default volume level

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def set_volume(ctx, volume: int):
    """Sets the volume level (1-100)."""
    global volume_level
    if 1 <= volume <= 100:
        volume_level = volume / 100.0  # Convert to a scale of 0.0 - 1.0
        await ctx.send(f"🔊 Volume set to {volume}%")
    else:
        await ctx.send("❌ Volume must be between 1 and 100.")

@bot.command()
async def create_playlist(ctx, playlist_name: str):
    """Creates a new playlist."""
    if playlist_name in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' already exists.")
    else:
        playlists[playlist_name] = []
        await ctx.send(f"✅ Created playlist '{playlist_name}'!")

@bot.command()
async def add_to_playlist(ctx, playlist_name: str, url: str):
    """Adds a song to a playlist."""
    if playlist_name not in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' does not exist.")
    else:
        playlists[playlist_name].append(url)
        await ctx.send(f"🎵 Added song to playlist '{playlist_name}'!")

@bot.command()
async def show_playlist(ctx, playlist_name: str):
    """Displays songs in a playlist."""
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f"❌ Playlist '{playlist_name}' is empty or does not exist.")
    else:
        playlist_songs = '\n'.join([f"{i+1}. {song}" for i, song in enumerate(playlists[playlist_name])])
        await ctx.send(f"📜 **Playlist '{playlist_name}':**\n{playlist_songs}")

@bot.command()
async def play_playlist(ctx, playlist_name: str):
    """Plays all songs from a playlist."""
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f"❌ Playlist '{playlist_name}' is empty or does not exist.")
    else:
        song_queue.extend(playlists[playlist_name])
        await ctx.send(f"▶️ Added playlist '{playlist_name}' to queue!")
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await play_next(ctx)

@bot.command()
async def delete_playlist(ctx, playlist_name: str):
    """Deletes a playlist."""
    if playlist_name in playlists:
        del playlists[playlist_name]
        await ctx.send(f"🗑 Playlist '{playlist_name}' deleted.")
    else:
        await ctx.send(f"❌ Playlist '{playlist_name}' does not exist.")

@bot.command()
async def join(ctx):
    """Bot joins the user's voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎧 Joined the voice channel!")
    else:
        await ctx.send("❌ You need to be in a voice channel first!")

@bot.command()
async def leave(ctx):
    """Bot disconnects from the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Left the voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def play(ctx, url: str = None):
    """Plays music from a YouTube URL or a playlist."""
    if not url:
        await ctx.send("❌ Please provide a YouTube link!")
        return
    
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)

        if 'entries' in info:  # Check if it's a playlist
            for entry in info['entries']:
                song_queue.append(entry['url'])  # Append each song URL to queue
            await ctx.send(f"🎵 Added **{len(info['entries'])}** songs from playlist to queue!")
        else:
            song_queue.append(info['url'])
            await ctx.send(f"🎵 Added to queue: **{info['title']}**")

    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    """Plays the next song in the queue and refreshes expired URLs."""
    global volume_level

    if ctx.voice_client and ctx.voice_client.is_playing():
        return  # Prevent overlapping plays

    if song_queue:
        url = song_queue.pop(0)  # Get the next song URL
        vc = ctx.voice_client

        def after_play(error):
            if error:
                print(f"Error playing audio: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
    try:
        info = ydl.extract_info(url, download=True)  # Force download

        if 'entries' in info:  # If it's a playlist, get the first entry
            info = info['entries'][0]

        # Get the actual filename
        audio_filename = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

        if not os.path.exists(audio_filename):
            raise FileNotFoundError(f"Downloaded audio file '{audio_filename}' not found.")

    except Exception as e:
        await ctx.send(f"⚠️ Error retrieving audio: {e}\nSkipping to next song...")
        return await play_next(ctx)

vc.play(discord.FFmpegPCMAudio(audio_filename, **FFMPEG_OPTIONS), after=after_play)        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)  # Apply volume level
        await ctx.send(f"▶️ Now playing: {info.get('title', 'Unknown title')} at {int(volume_level * 100)}% volume")
    else:
        await ctx.send("✅ Queue is empty!")
# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot.run(TOKEN)