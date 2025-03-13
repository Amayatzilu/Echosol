import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

# Load environment variables (Ensure TOKEN is stored in Railway Variables or .env file)
TOKEN = os.getenv("TOKEN")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Define music folder path for uploaded files
MUSIC_FOLDER = "downloads/"
os.makedirs(MUSIC_FOLDER, exist_ok=True)

# Configure YouTube downloader settings
cookies_path = "/app/cookies.txt"
cookie_data = os.getenv("YOUTUBE_COOKIES", "")

if cookie_data:
    with open(cookies_path, "w") as f:
        f.write(cookie_data)

# Configure YouTube downloader settings
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'False',
    'cookiefile': cookies_path,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': f'{MUSIC_FOLDER}%(title)s.%(ext)s',
    'quiet': True,
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    },
}

FFMPEG_OPTIONS = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

song_queue = []
playlists = {}
volume_level = 1.0  # Default volume level
uploaded_files = []  # List to store uploaded files

@bot.event
async def on_ready():
    global uploaded_files
    uploaded_files = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith(('.mp3', '.wav'))]
    print(f'Logged in as {bot.user}')

@bot.command()
async def join(ctx):
    """Joins a voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎧 Joined the voice channel!")
    else:
        await ctx.send("❌ You need to be in a voice channel first!")

@bot.command()
async def leave(ctx):
    """Leaves the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Left the voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def play(ctx, url: str = None):
    """Plays a song from YouTube or adds it to the queue."""
    if not url:
        await ctx.send("❌ Please provide a YouTube link!")
        return
    
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        
        if 'entries' in info:  # If a playlist is provided
            for entry in info['entries']:
                song_queue.append(entry['url'])
            await ctx.send(f"🎵 Added {len(info['entries'])} songs from the playlist to queue!")
        else:
            song_queue.append(info['url'])
            await ctx.send(f"🎵 Added to queue: **{info['title']}**")
    
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    """Plays the next song in the queue."""
    global volume_level
    if ctx.voice_client and ctx.voice_client.is_playing():
        return
    
    if song_queue:
        url = song_queue.pop(0)
        vc = ctx.voice_client
        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)
        await ctx.send(f"▶️ Now playing: {url}")
    else:
        await ctx.send("✅ Queue is empty!")

@bot.command()
async def pause(ctx):
    """Pauses the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸ Music paused!")

@bot.command()
async def resume(ctx):
    """Resumes paused music."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed music!")

@bot.command()
async def skip(ctx):
    """Skips the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await play_next(ctx)
        await ctx.send("⏭ Skipped to the next song!")

@bot.command()
async def volume(ctx, volume: int):
    """Sets the bot's volume."""
    global volume_level
    if 1 <= volume <= 100:
        volume_level = volume / 100.0
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume_level
        await ctx.send(f"🔊 Volume set to {volume}%")
    else:
        await ctx.send("❌ Volume must be between 1 and 100.")


@bot.command()
async def listsongs(ctx):
    """Lists available uploaded songs with numbered IDs."""
    global uploaded_files
    uploaded_files = [f for f in os.listdir(MUSIC_FOLDER) if f.endswith(('.mp3', '.wav'))]
    if uploaded_files:
        song_list = '\n'.join([f"{i+1}. {song}" for i, song in enumerate(uploaded_files)])
        await ctx.send(f"🎵 **Available Songs:**\n```{song_list}```\nUse `!play_number <number>` to play a song.")
    else:
        await ctx.send("❌ No songs found in the music folder!")

@bot.command()
async def playnumber(ctx, number: int):
    """Plays an uploaded song using its number from `!list_songs`."""
    global uploaded_files
    if 1 <= number <= len(uploaded_files):
        song_name = uploaded_files[number - 1]
        song_path = os.path.join(MUSIC_FOLDER, song_name)
    
        if ctx.voice_client is None:
            await ctx.invoke(join)

        vc = ctx.voice_client
        vc.play(discord.FFmpegPCMAudio(song_path, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)
        await ctx.send(f"▶️ Now playing: **{song_name}**")
    else:
        await ctx.send("❌ Invalid song number. Use `!list_songs` to see available songs.")

@bot.event
async def on_message(message):
    """Handles file uploads from users and updates the song list."""
    global uploaded_files
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.mp3', '.wav')):
                file_path = os.path.join(MUSIC_FOLDER, attachment.filename)
                await attachment.save(file_path)
                uploaded_files.append(attachment.filename)
                await message.channel.send(f"🎵 File received: **{attachment.filename}**. Use `!list_songs` to see available songs.")
    await bot.process_commands(message)

@bot.command()
async def stop(ctx):
    """Stops playback."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Music stopped!")
    else:
        await ctx.send("❌ No music is currently playing.")

@bot.command()
async def cp(ctx, playlist_name: str):
    """Creates a new playlist."""
    if playlist_name in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' already exists.")
    else:
        playlists[playlist_name] = []
        await ctx.send(f"✅ Created playlist '{playlist_name}'!")

@bot.command()
async def atp(ctx, playlist_name: str, url: str):
    """Adds a song to a playlist."""
    if playlist_name not in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' does not exist.")
    else:
        playlists[playlist_name].append(url)
        await ctx.send(f"🎵 Added song to playlist '{playlist_name}'!")

@bot.command()
async def sp(ctx, playlist_name: str):
    """Displays songs in a playlist."""
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f"❌ Playlist '{playlist_name}' is empty or does not exist.")
    else:
        playlist_songs = '\n'.join([f"{i+1}. {song}" for i, song in enumerate(playlists[playlist_name])])
        await ctx.send(f"📜 **Playlist '{playlist_name}':**\n{playlist_songs}")

@bot.command()
async def playlist(ctx, playlist_name: str):
    """Plays all songs from a playlist."""
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f"❌ Playlist '{playlist_name}' is empty or does not exist.")
    else:
        song_queue.extend(playlists[playlist_name])
        await ctx.send(f"▶️ Added playlist '{playlist_name}' to queue!")
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await play_next(ctx)

@bot.command()
async def dp(ctx, playlist_name: str):
    """Deletes a playlist."""
    if playlist_name in playlists:
        del playlists[playlist_name]
        await ctx.send(f"🗑 Playlist '{playlist_name}' deleted.")
    else:
        await ctx.send(f"❌ Playlist '{playlist_name}' does not exist.")

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot.run(TOKEN)
