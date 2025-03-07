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
    'noplaylist': 'False',  # Allow downloading from playlists
    'extract_flat': True,   # Extract playlist info without downloading all at once
    'cookiefile': cookies_path,  # Use the manually exported cookies
    'postprocessors': [{  # Ensure audio is extracted properly
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': 'temp_audio.%(ext)s',  # Save temp file before playing
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
                info = ydl.extract_info(url, download=False)
                
                # If it's a playlist, get the first entry
                if 'entries' in info:
                    info = info['entries'][0]
                
                # Ensure we get the correct direct URL
                audio_url = info.get('url')

                if not audio_url:
                    raise KeyError("No direct URL found for the video.")

            except Exception as e:
                await ctx.send(f"⚠️ Error retrieving audio: {e}\nSkipping to next song...")
                return await play_next(ctx)

        vc.play(discord.FFmpegPCMAudio("temp_audio.mp3", **FFMPEG_OPTIONS), after=after_play)
        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)  # Apply volume level
        await ctx.send(f"▶️ Now playing: {info.get('title', 'Unknown title')} at {int(volume_level * 100)}% volume")
    else:
        await ctx.send("✅ Queue is empty!")

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot.run(TOKEN)
