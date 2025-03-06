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
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True'
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
    """Plays music from a YouTube URL or the next song in queue."""
    if url:
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            song_queue.append(info)
            await ctx.send(f"🎵 Added to queue: **{info['title']}**")

        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await play_next(ctx)
    else:
        await ctx.send("❌ Please provide a YouTube link!")

async def play_next(ctx):
    """Plays the next song in the queue."""
    if song_queue:
        info = song_queue.pop(0)
        vc = ctx.voice_client
        URL = info['url']

        vc.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), 
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"▶️ Now playing: **{info['title']}**")
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
        queue_list = '\n'.join([f"{i+1}. {song['title']}" for i, song in enumerate(song_queue)])
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
        await play_next(ctx)
        await ctx.send("⏭ Skipped the current song!")
    else:
        await ctx.send("❌ No song is playing to skip.")

# Run the bot

TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot = commands.Bot(command_prefix="!")

bot.run(TOKEN)