import discord
from discord.ext import commands
import yt_dlp as youtube_dl

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Voice channel settings
FFMPEG_OPTIONS = {'options': '-vn'}

# Global Variables
song_queue = []  # Stores songs in the queue
playlists = {}   # Stores user-created playlists as {playlist_name: [song_urls]}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True'
}

@bot.command()
async def connect(ctx):
    """Bot joins the voice channel of the user."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎧 Joined the voice channel!")
    else:
        await ctx.send("❌ You need to be in a voice channel first!")

@bot.command()
async def disconnect(ctx):
    """Bot disconnects from the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Left the voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command()
async def play(ctx, url):
    """Plays music from a YouTube URL."""
    if not ctx.voice_client:  # If not connected, join the channel
        await ctx.invoke(join)

    await ctx.send(f"🎶 Fetching music from: {url} ...")

    # Extract the best audio source from the given YouTube URL
    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        URL = info['url']

    # Play the extracted audio
    vc = ctx.voice_client
    vc.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: print(f"Finished playing: {e}"))
    
    await ctx.send(f"▶️ Now playing: **{info['title']}**")

@bot.command()
async def stop(ctx):
    """Stops music playback."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Music stopped!")
    else:
        await ctx.send("❌ No music is currently playing.")

import random

# Song queue list
song_queue = []

@bot.command()
async def play(ctx, url=None):
    """Plays music from a YouTube URL or the next song in queue."""
    if url:
        # If a URL is provided, add it to the queue
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            song_queue.append(info)
            await ctx.send(f"🎵 Added to queue: **{info['title']}**")

        # If bot is not already playing, start playback
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await play_next(ctx)
    else:
        await ctx.send("❌ Please provide a YouTube link!")

async def play_next(ctx):
    """Plays the next song in the queue."""
    if song_queue:
        info = song_queue.pop(0)  # Get the first song from the queue
        vc = ctx.voice_client
        URL = info['url']

        vc.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"▶️ Now playing: **{info['title']}**")
    else:
        await ctx.send("✅ Queue is empty!")

@bot.command()
async def shuffle(ctx):
    """Shuffles the current queue."""
    if len(song_queue) > 1:
        random.shuffle(song_queue)
        await ctx.send("🔀 The queue has been shuffled!")
    else:
        await ctx.send("❌ Not enough songs in the queue to shuffle.")

@bot.command()
async def createplaylist(ctx, name: str):
    """Creates a new playlist."""
    if name in playlists:
        await ctx.send(f"❌ Playlist **{name}** already exists!")
    else:
        playlists[name] = []
        await ctx.send(f"✅ Playlist **{name}** has been created!")

@bot.command()
async def addtoplaylist(ctx, name: str, url: str):
    """Adds a song to an existing playlist."""
    if name in playlists:
        playlists[name].append(url)
        await ctx.send(f"🎵 Added song to playlist **{name}**!")
    else:
        await ctx.send(f"❌ Playlist **{name}** does not exist. Use `!create_playlist {name}` first.")

@bot.command()
async def showplaylist(ctx, name: str):
    """Displays the songs in a playlist."""
    if name in playlists and playlists[name]:
        playlist_songs = "\n".join([f"{i+1}. {song}" for i, song in enumerate(playlists[name])])
        await ctx.send(f"📜 **Playlist - {name}:**\n{playlist_songs}")
    else:
        await ctx.send(f"❌ Playlist **{name}** is empty or does not exist.")

@bot.command()
async def playplaylist(ctx, name: str):
    """Plays all songs from a saved playlist."""
    if name in playlists and playlists[name]:
        for url in playlists[name]:
            with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                song_queue.append(info)
        
        await ctx.send(f"🎶 Added **{len(playlists[name])} songs** from playlist **{name}** to the queue!")

        # If nothing is currently playing, start playback
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await play_next(ctx)
    else:
        await ctx.send(f"❌ Playlist **{name}** is empty or does not exist.")

@bot.command()
async def deleteplaylist(ctx, name: str):
    """Deletes a playlist."""
    if name in playlists:
        del playlists[name]
        await ctx.send(f"🗑 Playlist **{name}** has been deleted!")
    else:
        await ctx.send(f"❌ Playlist **{name}** does not exist.")



import os
from discord.ext import commands

TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot = commands.Bot(command_prefix="!")

bot.run(TOKEN)
