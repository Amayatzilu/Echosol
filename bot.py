import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random

# Load environment variables (Ensure TOKEN is stored in Railway Variables or .env file)
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Allow the bot to track server members (including itself)

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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disables default help

@bot.command(aliases=["lost", "helfen","aide"])
async def help(ctx):
    """Displays all main commands."""
    help_text = "**🎵 Available Commands:**\n"
    
    for command in bot.commands:
        if not command.hidden:  # Ignores hidden commands
            help_text += f"**!{command.name}** - {command.help}\n"
    
    await ctx.send(help_text)

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

@bot.command(aliases=["playwithme", "connect", "verbinden", "rejoindre"])
async def join(ctx):
    """Joins a voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎧 Joined the voice channel!")
    else:
        await ctx.send("❌ You need to be in a voice channel first!")

@bot.command(aliases=["goaway", "disconnect", "verlassen", "partir"])
async def leave(ctx):
    """Leaves the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Left the voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command(aliases=["p", "gimme", "spielen", "jouer"])
async def play(ctx, url: str = None):
    """Plays a song from YouTube or adds it to the queue."""
    if not url:
        await ctx.send("❌ Please provide a YouTube link!")
        return

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to play music!")
            return

    try:
        with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)

            if 'entries' in info:  # Playlist
                added = 0
                for entry in info['entries']:
                    if entry:
                        if '_type' in entry and entry['_type'] == 'url':
                            entry_info = ydl.extract_info(entry['url'], download=False)
                        else:
                            entry_info = entry
                        song_queue.append((entry_info['webpage_url'], entry_info['title']))
                        added += 1
                await ctx.send(f"🎵 Added {added} songs from the playlist to the queue!")
            else:  # Single video
                song_queue.append((info['webpage_url'], info['title']))
                await ctx.send(f"🎵 Added to queue: **{info['title']}**")

    except Exception as e:
        await ctx.send(f"⚠️ Error adding song: {e}")
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
async def play_next(ctx):
    """Plays the next song in the queue, handling both YouTube and uploaded files."""
    global volume_level
    if ctx.voice_client and ctx.voice_client.is_playing():
        return

    if song_queue:
        song_data = song_queue.pop(0)  # Get the next song

        # Check if it's a YouTube song (tuple) or an uploaded file (string path)
        if isinstance(song_data, tuple):
            original_url, song_title = song_data
            with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(original_url, download=False)
                    song_url = info['url']  # Refreshed YouTube stream link
                except Exception as e:
                    await ctx.send(f"⚠️ Error retrieving audio: {e}\nSkipping to next song...")
                    return await play_next(ctx)
        else:
            song_url = song_data  # Local file
            song_title = os.path.basename(song_url)

        vc = ctx.voice_client

        def after_play(error):
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        vc.play(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS), after=after_play)
        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)
        await ctx.send(f"▶️ Now playing: **{song_title}**")
    else:
        await ctx.send("✅ Queue is empty!")

@bot.command(aliases=["mixitup", "mischen", "shuff"])
async def shuffle(ctx):
    """Shuffles the current music queue."""
    if len(song_queue) > 1:
        random.shuffle(song_queue)
        await ctx.send("🔀 The queue has been shuffled!")
    else:
        await ctx.send("❌ Not enough songs in the queue to shuffle.")

@bot.command(aliases=["hush"])
async def pause(ctx):
    """Pauses the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸ Music paused!")

@bot.command(aliases=["youmayspeak"])
async def resume(ctx):
    """Resumes paused music."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed music!")

@bot.command(aliases=["nextplease"])
async def skip(ctx):
    """Skips the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await play_next(ctx)
        await ctx.send("⏭ Skipped to the next song!")

@bot.command(aliases=["turnitup", "tooloud", "v"])
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

@bot.command(aliases=["whatsnext", "q"])
async def queue(ctx):
    """Displays the current queue with pagination and shuffle button."""
    if not song_queue:
        await ctx.send("❌ The queue is empty.")
        return

    class QueuePages(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.page = 0
            self.items_per_page = 10

        async def send_page(self, interaction):
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            page_items = song_queue[start:end]
            if not page_items:
                await interaction.response.send_message("❌ No items on this page.", ephemeral=True)
                return

            queue_display = '\n'.join([
                f"{i+1}. {os.path.basename(song[1]) if isinstance(song, tuple) else os.path.basename(song)}"
                for i, song in enumerate(page_items, start=start)
            ])
            await interaction.response.edit_message(content=f"📜 **Queue Page {self.page + 1}:**\n```{queue_display}```", view=self)

        @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
        async def prev_page(self, interaction: discord.Interaction, button: Button):
            if self.page > 0:
                self.page -= 1
                await self.send_page(interaction)

        @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
        async def next_page(self, interaction: discord.Interaction, button: Button):
            max_pages = (len(song_queue) - 1) // self.items_per_page
            if self.page < max_pages:
                self.page += 1
                await self.send_page(interaction)

        @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.primary)
        async def shuffle_button(self, interaction: discord.Interaction, button: Button):
            import random
            random.shuffle(song_queue)
            self.page = 0
            await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)
            await self.send_page(interaction)

    view = QueuePages()
    start = 0
    end = start + view.items_per_page
    page_items = song_queue[start:end]
    queue_display = '\n'.join([
        f"{i+1}. {os.path.basename(song[1]) if isinstance(song, tuple) else os.path.basename(song)}"
        for i, song in enumerate(page_items, start=start)
    ])
    await ctx.send(f"📜 **Queue Page 1:**\n```{queue_display}```", view=view)

from discord.ui import View, Button, Select
import math

@bot.command(aliases=["whatwegot"])
async def listsongs(ctx):
    """Lists available uploaded songs with pagination and play option."""
    if not uploaded_files:
        await ctx.send("❌ No songs found in the music folder!")
        return

    per_page = 10
    total_pages = math.ceil(len(uploaded_files) / per_page)
    range_size = 25  # Max pages shown per dropdown range
    page_range_index = 0  # Start with first 25 pages
    current_page = 0

    def get_page_embed(page_index):
        start = page_index * per_page
        end = start + per_page
        page = uploaded_files[start:end]
        song_list = "\n".join([f"{start + i + 1}. {song}" for i, song in enumerate(page)])
        embed = discord.Embed(
            title=f"🎵 Uploaded Songs (Page {page_index + 1}/{total_pages})",
            description=song_list,
            color=discord.Color.purple()
        )
        embed.set_footer(text="Use !playnumber <number> to play a song.")
        return embed

    class PageSelector(Select):
        def __init__(self, view):
            self.view = view
            self.update_options()
            super().__init__(placeholder="Jump to page...", options=self.view.page_options)

        def update_options(self):
            start_page = self.view.page_range_index * range_size
            end_page = min(start_page + range_size, total_pages)
            self.view.page_options = [
                discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(start_page, end_page)
            ]

        async def callback(self, interaction: discord.Interaction):
            self.view.current_page = int(self.values[0])
            await interaction.response.edit_message(embed=get_page_embed(self.view.current_page), view=self.view)

    class PaginationView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.current_page = 0
            self.page_range_index = 0
            self.page_options = []
            self.selector = PageSelector(self)
            self.add_item(self.selector)

        @discord.ui.button(label="⏮️ Prev", style=discord.ButtonStyle.blurple)
        async def prev_page(self, interaction: discord.Interaction, button: Button):
            if self.current_page > 0:
                self.current_page -= 1
                await interaction.response.edit_message(embed=get_page_embed(self.current_page), view=self)

        @discord.ui.button(label="▶️ Play This Page", style=discord.ButtonStyle.green)
        async def play_this_page(self, interaction: discord.Interaction, button: Button):
            start = self.current_page * per_page
            end = start + per_page
            added = []
            for filename in uploaded_files[start:end]:
                song_path = os.path.join(MUSIC_FOLDER, filename)
                song_queue.append(song_path)
                added.append(filename)
            await interaction.response.send_message(
                f"🎶 Added {len(added)} songs from page {self.current_page + 1} to queue!",
                ephemeral=True
            )
            if not ctx.voice_client or not ctx.voice_client.is_playing():
                if not ctx.voice_client and ctx.author.voice:
                    await ctx.author.voice.channel.connect()
                await play_next(ctx)

        @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: Button):
            if self.current_page < total_pages - 1:
                self.current_page += 1
                await interaction.response.edit_message(embed=get_page_embed(self.current_page), view=self)

        @discord.ui.button(label="🔁 Prev Range", style=discord.ButtonStyle.secondary, row=1)
        async def prev_range(self, interaction: discord.Interaction, button: Button):
            if self.page_range_index > 0:
                self.page_range_index -= 1
                self.refresh_dropdown()
                await interaction.response.edit_message(view=self)

        @discord.ui.button(label="🔁 Next Range", style=discord.ButtonStyle.secondary, row=1)
        async def next_range(self, interaction: discord.Interaction, button: Button):
            max_index = (total_pages - 1) // range_size
            if self.page_range_index < max_index:
                self.page_range_index += 1
                self.refresh_dropdown()
                await interaction.response.edit_message(view=self)

        def refresh_dropdown(self):
            self.remove_item(self.selector)
            self.selector.update_options()
            self.selector = PageSelector(self)
            self.add_item(self.selector)

    view = PaginationView()
    await ctx.send(embed=get_page_embed(current_page), view=view)

@bot.command(aliases=["pp", "seite", "page"])
async def playpage(ctx, *pages):
    """Plays one or more pages of uploaded songs."""
    per_page = 10
    total_pages = (len(uploaded_files) + per_page - 1) // per_page
    added = []

    if not pages:
        await ctx.send("❌ Please provide one or more page numbers (e.g. `!page 1 2 3`).")
        return

    for page_str in pages:
        try:
            page = int(page_str)
            if page < 1 or page > total_pages:
                await ctx.send(f"❌ Page {page} is out of range. Skipping.")
                continue

            start = (page - 1) * per_page
            end = start + per_page
            for filename in uploaded_files[start:end]:
                song_path = os.path.join(MUSIC_FOLDER, filename)
                song_queue.append(song_path)
                added.append(filename)
        except ValueError:
            await ctx.send(f"❌ `{page_str}` is not a valid number. Skipping.")

    if not added:
        await ctx.send("❌ No songs were added to the queue.")
        return

    await ctx.send(f"🎶 Added {len(added)} songs from page(s) {', '.join(pages)} to the queue!")

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to play music!")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["number", "n"])
async def playnumber(ctx, *numbers):
    """Plays one or multiple uploaded songs using their numbers."""
    added_songs = []
    for num in numbers:
        try:
            num = int(num.strip(','))  # Remove commas and convert to integer
            if 1 <= num <= len(uploaded_files):
                song_path = os.path.join(MUSIC_FOLDER, uploaded_files[num - 1])
                song_queue.append(song_path)
                added_songs.append(uploaded_files[num - 1])
            else:
                await ctx.send(f"❌ Invalid song number: {num}. Use `!listsongs` to see available songs.")
        except ValueError:
            await ctx.send(f"❌ Invalid input: {num}. Use numbers separated by spaces or commas.")

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to play music!")
            return
    
    if added_songs:
        await ctx.send(f"🎵 Added to queue: {', '.join(added_songs)}")
    
    # Auto-play if nothing is currently playing
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await play_next(ctx)

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
                await message.channel.send(f"🎵 File received: **{attachment.filename}**. Use `!listsongs` to see available songs.")
    await bot.process_commands(message)

@bot.command(aliases=["shutup", "nomore", "stoppen"])
async def stop(ctx):
    """Stops playback."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Music stopped!")
    else:
        await ctx.send("❌ No music is currently playing.")

@bot.command(aliases=["cp"])
async def createplaylist(ctx, playlist_name: str):
    """Creates a new playlist."""
    if playlist_name in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' already exists.")
    else:
        playlists[playlist_name] = []
        await ctx.send(f"✅ Created playlist '{playlist_name}'!")

@bot.command(aliases=["cpq"])
async def createplaylistqueue(ctx, playlist_name: str):
    """Creates a new playlist using the current queue."""
    if playlist_name in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' already exists.")
    elif not song_queue:
        await ctx.send("❌ The queue is empty, cannot create playlist.")
    else:
        playlists[playlist_name] = song_queue.copy()
        await ctx.send(f"✅ Created playlist '{playlist_name}' from current queue!")

@bot.command(aliases=["atp"])
async def addtoplaylist(ctx, playlist_name: str, url: str):
    """Adds a song to a playlist."""
    if playlist_name not in playlists:
        await ctx.send(f"❌ Playlist '{playlist_name}' does not exist.")
    else:
        playlists[playlist_name].append(url)
        await ctx.send(f"🎵 Added song to playlist '{playlist_name}'!")
    if 1 <= number <= len(uploaded_files):
        song_name = uploaded_files[number - 1]
        song_path = os.path.join(MUSIC_FOLDER, song_name)
        playlists[playlist_name].append(song_path)
        await ctx.send(f"🎵 Added **{song_name}** to playlist '{playlist_name}'!")
    else:
        await ctx.send("❌ Invalid song number. Use `!list_songs` to see available songs.")

@bot.command(aliases=["sp"])
async def showplaylist(ctx, playlist_name: str):
    """Displays songs in a playlist with pagination and shuffle."""
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f"❌ Playlist '{playlist_name}' is empty or does not exist.")
        return

    songs = playlists[playlist_name]
    page = 0
    items_per_page = 10

    def get_page_embed():
        start = page * items_per_page
        end = start + items_per_page
        current_page_songs = songs[start:end]
        embed = discord.Embed(
            title=f"📜 Playlist '{playlist_name}'",
            description='\n'.join([f"{i+1+start}. {song}" for i, song in enumerate(current_page_songs)]),
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Page {page+1}/{(len(songs) + items_per_page - 1) // items_per_page}")
        return embed

    class PlaylistView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.message = None

        @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.secondary)
        async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
            nonlocal page
            if page > 0:
                page -= 1
                await interaction.response.edit_message(embed=get_page_embed(), view=self)

        @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            nonlocal page
            if (page + 1) * items_per_page < len(songs):
                page += 1
                await interaction.response.edit_message(embed=get_page_embed(), view=self)

        @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.success)
        async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            import random
            random.shuffle(playlists[playlist_name])
            await interaction.response.edit_message(embed=get_page_embed(), view=self)

    view = PlaylistView()
    await ctx.send(embed=get_page_embed(), view=view)

@bot.command(aliases=["playlist"])
async def loadplaylist(ctx, playlist_name: str):
    """Plays all songs from a playlist."""
    if playlist_name not in playlists or not playlists[playlist_name]:
        await ctx.send(f"❌ Playlist '{playlist_name}' is empty or does not exist.")
    else:
        song_queue.extend(playlists[playlist_name])
        await ctx.send(f"▶️ Added playlist '{playlist_name}' to queue!")
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            await play_next(ctx)

@bot.command(aliases=["dp"])
async def deleteplaylist(ctx, playlist_name: str):
    """Deletes a playlist."""
    if playlist_name in playlists:
        del playlists[playlist_name]
        await ctx.send(f"🗑 Playlist '{playlist_name}' deleted.")
    else:
        await ctx.send(f"❌ Playlist '{playlist_name}' does not exist.")

@bot.command(aliases=["spankies", "cq"])
async def clearqueue(ctx):
    """Clears the music queue."""
    global song_queue
    song_queue = []  # Empty the queue
    await ctx.send("🗑️ Cleared the music queue!")

@bot.command(aliases=["exterminate", "cu"])
async def clearuploads(ctx):
    """Deletes all uploaded files to free space."""
    global uploaded_files
    file_count = 0

    for filename in os.listdir(MUSIC_FOLDER):
        file_path = os.path.join(MUSIC_FOLDER, filename)
        if filename.endswith(('.mp3', '.wav')):  # Only delete audio files
            os.remove(file_path)  # Delete the file
            file_count += 1

    uploaded_files = []  # Reset the uploaded files list
    await ctx.send(f"🗑️ Deleted {file_count} uploaded files.")

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot.run(TOKEN)