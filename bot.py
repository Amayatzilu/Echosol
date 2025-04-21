import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

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

@bot.command(aliases=["lost", "helfen"])
async def help(ctx):
    """Displays all main commands, grouped by category."""
    embed = discord.Embed(title="🎶 Echosol Help", color=discord.Color.blurple())
    embed.set_footer(text="Use commands as shown. Aliases are supported for most.")

    embed.add_field(
        name="🎵 Playback",
        value=(
            "**!play** – Plays a song from YouTube or adds it to the queue.\n"
            "**!pause** – Pauses the current song.\n"
            "**!resume** – Resumes paused music.\n"
            "**!skip** – Skips the current song.\n"
            "**!stop** – Stops playback and clears the queue.\n"
            "**!volume** – Sets the bot's volume.\n"
            "**!shuffle** – Shuffles the current music queue.\n"
            "**!queue** – Displays the current queue with pagination and shuffle button."
        ),
        inline=False
    )

    embed.add_field(
        name="📁 Uploads & Playback",
        value=(
            "**!listsongs** – Lists available uploaded songs with optional tag filter, pagination, and actions.\n"
            "**!playbynumber** – Plays one or multiple uploaded songs using their numbers.\n"
            "**!playbypage** – Plays one or more pages of uploaded songs.\n"
            "**!playalluploads** – Adds all uploaded songs to the queue in shuffled order.\n"
            "**!removeupload** – Removes a specific uploaded song by its number (from !listsongs).\n"
            "**!clearuploads** – Deletes all uploaded files to free space."
        ),
        inline=False
    )

    embed.add_field(
        name="🏷️ Tagging System",
        value=(
            "**!tag** – Tags one or more uploaded songs. Usage: `!tag <number(s)> <tags...>`\n"
            "**!playbytag** – Plays all uploaded songs that match one or more tags. Usage: `!playbytag chill vibe`\n"
            "**!listtags** – Shows all tags currently in use for uploaded songs."
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Utility",
        value=(
            "**!join** – Joins a voice channel.\n"
            "**!leave** – Leaves the voice channel.\n"
            "**!clearqueue** – Clears the music queue.\n"
            "**!help** – Displays all main commands."
        ),
        inline=False
    )

    await ctx.send(embed=embed)

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
file_tags = {}  # Structure: {'filename': ['tag1', 'tag2'], ...}
pending_tag_uploads = {}

@bot.event
async def on_message(message):
    global uploaded_files, file_tags, pending_tag_uploads

    # Allow bot to continue processing commands
    await bot.process_commands(message)

    # Ignore messages from bots
    if message.author.bot:
        return

    # If attachments are being uploaded
    if message.attachments:
        new_files = []
        for attachment in message.attachments:
            if attachment.filename.endswith(('.mp3', '.wav')):
                file_path = os.path.join(MUSIC_FOLDER, attachment.filename)
                await attachment.save(file_path)
                uploaded_files.append(attachment.filename)
                new_files.append(attachment.filename)

        if new_files:
            pending_tag_uploads[message.author.id] = new_files
            await message.channel.send(
                f"🎵 Received {len(new_files)} file(s): {', '.join(new_files)}.\n"
                f"🔖 Please reply to this message with tags (separated by spaces or commas)!"
            )
        return

    # Handle replies with tags
    if message.reference and message.author.id in pending_tag_uploads:
        tags = [t.strip().lower() for t in message.content.replace(",", " ").split()]
        if not tags:
            await message.channel.send("❌ No tags provided. Please try again.")
            return

        for filename in pending_tag_uploads[message.author.id]:
            if filename not in file_tags:
                file_tags[filename] = []
            file_tags[filename].extend(tags)

        await message.channel.send(
            f"🏷 Tagged **{len(pending_tag_uploads[message.author.id])}** file(s) with: `{', '.join(tags)}`"
        )

        del pending_tag_uploads[message.author.id]

@bot.command(aliases=["playwithme", "connect", "verbinden"])
async def join(ctx):
    """Joins a voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🎧 Joined the voice channel!")
    else:
        await ctx.send("❌ You need to be in a voice channel first!")

@bot.command(aliases=["goaway", "disconnect", "verlassen"])
async def leave(ctx):
    """Leaves the voice channel."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🔇 Left the voice channel!")
    else:
        await ctx.send("❌ I'm not in a voice channel.")

@bot.command(aliases=["p", "gimme", "spielen"])
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

def get_local_duration(path):
    try:
        if path.endswith(".mp3"):
            return int(MP3(path).info.length)
        elif path.endswith(".wav"):
            return int(WAVE(path).info.length)
    except:
        pass
    return 0

async def play_next(ctx):
    global volume_level
    if ctx.voice_client and ctx.voice_client.is_playing():
        return

    if song_queue:
        song_data = song_queue.pop(0)

        if isinstance(song_data, tuple):
            original_url, song_title = song_data
            try:
                with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(original_url, download=False)
                    song_url = info['url']
                    duration = info.get('duration', 0)
            except Exception as e:
                await ctx.send(f"⚠️ Could not fetch audio: {e}\nSkipping to next song...")
                return await play_next(ctx)
        else:
            song_url = song_data
            song_title = os.path.basename(song_url)
            try:
                if song_url.endswith(".mp3"):
                    audio = MP3(song_url)
                elif song_url.endswith(".wav"):
                    audio = WAVE(song_url)
                else:
                    audio = None
                duration = int(audio.info.length) if audio else 0
            except Exception as e:
                await ctx.send(f"⚠️ Failed to read file duration: {e}")
                duration = 0

        vc = ctx.voice_client

        def after_play(error):
            if error:
                print(f"⚠️ Playback error: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        vc.play(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS), after=after_play)
        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)

        # Display initial Now Playing embed
        embed = discord.Embed(title="🎵 Now Playing", description=f"**{song_title}**", color=discord.Color.green())
        if duration:
            embed.add_field(name="Progress", value="`[░░░░░░░░░░]` 0:00", inline=False)
        message = await ctx.send(embed=embed)

        # Update progress bar if duration is known
        if duration:
            progress_bar_length = 10
            for second in range(duration):
                filled = int((second / duration) * progress_bar_length)
                empty = progress_bar_length - filled
                bar = "█" * filled + "░" * empty
                embed.set_field_at(0, name="Progress", value=f"`[{bar}]` {second//60}:{second%60:02d}", inline=False)
                try:
                    await message.edit(embed=embed)
                except discord.HTTPException:
                    pass
                await asyncio.sleep(1)
        else:
            await message.edit(content=f"▶️ Now playing: **{song_title}**")

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

@bot.command(aliases=["nextplease", "skippy"])
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
    """Lists available uploaded songs with optional tag filter, pagination, and actions."""
    if not uploaded_files:
        await ctx.send("❌ No songs found in the music folder!")
        return

    per_page = 10
    range_size = 25
    all_tags = sorted(set(tag for tags in file_tags.values() for tag in tags))

    # Holds the filtered song list and view state
    class State:
        def __init__(self):
            self.current_page = 0
            self.page_range_index = 0
            self.filtered_files = uploaded_files.copy()
            self.selected_tag = None

    state = State()

    def get_page_embed():
        start = state.current_page * per_page
        end = start + per_page
        page = state.filtered_files[start:end]

        song_list = ""
        for i, song in enumerate(page):
            line = f"{start + i + 1}. {song}"
            song_list += line + "\n"

        total_pages = max(1, math.ceil(len(state.filtered_files) / per_page))
        title = f"🎵 Uploaded Songs"
        if state.selected_tag:
            title += f" - Tag: {state.selected_tag}"
        embed = discord.Embed(
            title=title + f" (Page {state.current_page + 1}/{total_pages})",
            description=song_list or "No songs found on this page.",
            color=discord.Color.purple()
        )
        return embed

    class TagSelector(Select):
        def __init__(self):
            options = [discord.SelectOption(label="All", value="all")] + [
                discord.SelectOption(label=tag, value=tag) for tag in all_tags
            ]
            super().__init__(placeholder="Filter by tag...", options=options)

        async def callback(self, interaction: discord.Interaction):
            choice = self.values[0]
            state.selected_tag = None if choice == "all" else choice
            state.current_page = 0
            state.page_range_index = 0
            if state.selected_tag:
                state.filtered_files = [f for f in uploaded_files if state.selected_tag in file_tags.get(f, [])]
            else:
                state.filtered_files = uploaded_files.copy()
            await interaction.response.edit_message(embed=get_page_embed(), view=view)

    class PaginationView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.selector = TagSelector()
            self.add_item(self.selector)

        @discord.ui.button(label="⏮️ Prev", style=discord.ButtonStyle.blurple)
        async def prev_page(self, interaction: discord.Interaction, button: Button):
            if state.current_page > 0:
                state.current_page -= 1
                await interaction.response.edit_message(embed=get_page_embed(), view=self)

        @discord.ui.button(label="▶️ Play This Page", style=discord.ButtonStyle.green)
        async def play_page(self, interaction: discord.Interaction, button: Button):
            start = state.current_page * per_page
            end = start + per_page
            added = []
            for filename in state.filtered_files[start:end]:
                song_path = os.path.join(MUSIC_FOLDER, filename)
                song_queue.append(song_path)
                added.append(filename)
            await interaction.response.send_message(f"🎶 Queued {len(added)} songs from this page!", ephemeral=True)

            if not ctx.voice_client or not ctx.voice_client.is_playing():
                if not ctx.voice_client and ctx.author.voice:
                    await ctx.author.voice.channel.connect()
                await play_next(ctx)

        @discord.ui.button(label="🔀 Shuffle This Page", style=discord.ButtonStyle.primary)
        async def shuffle_page(self, interaction: discord.Interaction, button: Button):
            start = state.current_page * per_page
            end = start + per_page
            page = state.filtered_files[start:end]
            random.shuffle(page)
            added = []
            for filename in page:
                song_path = os.path.join(MUSIC_FOLDER, filename)
                song_queue.append(song_path)
                added.append(filename)
            await interaction.response.send_message(f"🔀 Queued {len(added)} shuffled songs from this page.", ephemeral=True)

            if not ctx.voice_client or not ctx.voice_client.is_playing():
                if not ctx.voice_client and ctx.author.voice:
                    await ctx.author.voice.channel.connect()
                await play_next(ctx)

        @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: Button):
            total_pages = max(1, math.ceil(len(state.filtered_files) / per_page))
            if state.current_page < total_pages - 1:
                state.current_page += 1
                await interaction.response.edit_message(embed=get_page_embed(), view=self)

        @discord.ui.button(label="🔁 Prev Range", style=discord.ButtonStyle.secondary, row=1)
        async def prev_range(self, interaction: discord.Interaction, button: Button):
            if state.page_range_index > 0:
                state.page_range_index -= 1
                await interaction.response.edit_message(view=self)

        @discord.ui.button(label="🔁 Next Range", style=discord.ButtonStyle.secondary, row=1)
        async def next_range(self, interaction: discord.Interaction, button: Button):
            total_pages = max(1, math.ceil(len(state.filtered_files) / per_page))
            max_index = (total_pages - 1) // range_size
            if state.page_range_index < max_index:
                state.page_range_index += 1
                await interaction.response.edit_message(view=self)

    view = PaginationView()
    await ctx.send(embed=get_page_embed(), view=view)

@bot.command(aliases=["everything", "alle", "expulso", "mruniverse"])
async def playalluploads(ctx):
    """Adds all uploaded songs to the queue in shuffled order."""
    if not uploaded_files:
        await ctx.send("❌ No uploaded songs found.")
        return

    # Shuffle a copy of the uploaded file list
    shuffled_songs = uploaded_files[:]
    random.shuffle(shuffled_songs)

    # Queue them
    for filename in shuffled_songs:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue.append(song_path)

    await ctx.send(f"🎶 Shuffled and queued **{len(shuffled_songs)}** uploaded songs!")

    # Connect and start playing
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to play music!")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["deleteit", "deleteupload", "ru"])
async def removeupload(ctx, number: int):
    """Removes a specific uploaded song by its number (from !listsongs)."""
    if number < 1 or number > len(uploaded_files):
        await ctx.send(f"❌ Invalid number. Use `!listsongs` to see available songs.")
        return

    filename = uploaded_files[number - 1]
    file_path = os.path.join(MUSIC_FOLDER, filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            uploaded_files.remove(filename)
            if filename in file_tags:
                del file_tags[filename]  # Also remove associated tags if present
            await ctx.send(f"🗑️ Removed **{filename}** from uploads.")
        else:
            await ctx.send("⚠️ File not found on disk.")
    except Exception as e:
        await ctx.send(f"❌ Failed to delete file: {e}")

@bot.command(aliases=["pp", "seite", "page", "playpage"])
async def playbypage(ctx, *pages):
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

@bot.command(aliases=["number", "playnumber", "n"])
async def playbynumber(ctx, *numbers):
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

@bot.command(aliases=["flag", "etikett"])
async def tag(ctx, *args):
    """Tags one or more uploaded songs. Usage: !tag <number(s)> <tags...>"""
    if len(args) < 2:
        await ctx.send("❌ Usage: `!tag <song number(s)> <tags>` — Example: `!tag 1 2 chill vibe`")
        return

    try:
        # Split numbers and tags
        numbers = [int(arg) for arg in args if arg.isdigit()]
        tags = [arg.lower() for arg in args if not arg.isdigit()]
    except ValueError:
        await ctx.send("❌ Invalid input. Song numbers must be integers.")
        return

    if not numbers or not tags:
        await ctx.send("❌ Please provide both song number(s) and at least one tag.")
        return

    tagged = []
    for num in numbers:
        if 1 <= num <= len(uploaded_files):
            filename = uploaded_files[num - 1]
            if filename not in file_tags:
                file_tags[filename] = []
            for tag in tags:
                if tag not in file_tags[filename]:
                    file_tags[filename].append(tag)
            tagged.append(filename)
        else:
            await ctx.send(f"⚠️ Skipped invalid song number: {num}")

    if tagged:
        await ctx.send(f"🏷️ Tagged songs: {', '.join(tagged)} with: `{', '.join(tags)}`")
    else:
        await ctx.send("❌ No valid songs tagged.")

@bot.command(aliases=["tagplay", "greenflag"])
async def playbytag(ctx, *search_tags):
    """Plays all uploaded songs that match one or more tags. Usage: !playbytag chill vibe"""
    if not search_tags:
        await ctx.send("❌ Please provide at least one tag. Example: `!playbytag chill`")
        return

    tags_lower = [t.lower() for t in search_tags]
    matched = [f for f in uploaded_files if any(tag in file_tags.get(f, []) for tag in tags_lower)]

    if not matched:
        await ctx.send(f"❌ No songs found with tag(s): `{', '.join(tags_lower)}`")
        return

    # Add matched songs to the queue
    for filename in matched:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue.append(song_path)

    await ctx.send(f"🎶 Added {len(matched)} songs with tag(s) `{', '.join(tags_lower)}` to the queue!")

    # Auto-play if nothing is currently playing
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to play music!")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["whiteflag", "viewtags", "showtags"])
async def listtags(ctx):
    """Shows all tags currently in use for uploaded songs."""
    if not file_tags:
        await ctx.send("❌ No tags have been added yet.")
        return

    # Collect all unique tags
    unique_tags = set()
    for tags in file_tags.values():
        unique_tags.update(tags)

    if not unique_tags:
        await ctx.send("❌ No tags found.")
        return

    sorted_tags = sorted(unique_tags)
    tag_text = ", ".join(sorted_tags)

    embed = discord.Embed(
        title="🏷️ Current Tags in Use",
        description=tag_text,
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["shutup", "nomore", "stoppen"])
async def stop(ctx):
    """Stops playback and clears the queue."""
    global song_queue
    song_queue.clear()  # Clear the queue

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹ Music stopped and queue cleared!")
    else:
        await ctx.send("⏹ No music was playing, but the queue has been cleared!")

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