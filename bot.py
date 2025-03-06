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
}

FFMPEG_OPTIONS = {'options': '-vn'}

song_queue = []  # Queue for storing songs

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

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
    """Plays the next song in the queue."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        return  # Prevent overlapping plays
    
    if song_queue:
        url = song_queue.pop(0)  # Get the next song URL
        vc = ctx.voice_client
        
        def after_play(error):
            if error:
                print(f"Error playing audio: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=after_play)
        await ctx.send(f"▶️ Now playing: {url}")
    else:
        await ctx.send("✅ Queue is empty!")

@bot.command()
async def stop(ctx):
    """Stops music playback."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Music stopped!")
    else:
        await ctx.send("❌ No music is currently playing.")

@bot.command()
async def queue(ctx):
    """Displays the current queue."""
    if song_queue:
        queue_list = '\n'.join([f"{i+1}. {song}" for i, song in enumerate(song_queue)])
        await ctx.send(f"📜 **Current Queue:**\n{queue_list}")
    else:
        await ctx.send("❌ The queue is empty.")

@bot.command()
async def shuffle(ctx):
    """Shuffles the queue."""
    import random
    if len(song_queue) > 1:
        random.shuffle(song_queue)
        await ctx.send("🔀 The queue has been shuffled!")
    else:
        await ctx.send("❌ Not enough songs in the queue to shuffle.")

@bot.command()
async def skip(ctx):
    """Skips the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Skipped the current song!")
        await play_next(ctx)
    else:
        await ctx.send("❌ No song is playing to skip.")

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot.run(TOKEN)