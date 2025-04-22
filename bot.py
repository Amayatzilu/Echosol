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
    embed = discord.Embed(
        title="✨ Welcome to Echosol, your heart's musical companion 💖",
        description="Let the rhythm guide your soul and the light lead your playlist 🌈🎵",
        color=discord.Color.from_str("#ffe680")
    )
    embed.set_footer(text="🌻 Shine bright, share the light – your musical journey starts here.")

    embed.add_field(
        name="🌞 Playback – Light up the room!",
        value=(
            "🎶 **!play** – Bring in a melody from YouTube or add it to the mix.\n"
            "⏸️ **!pause** – Gently pause your sunshine soundtrack.\n"
            "▶️ **!resume** – Pick up right where the glow left off.\n"
            "⏭️ **!skip** – Skip forward with radiant rhythm.\n"
            "⏹️ **!stop** – Bring the music to a gentle halt & clear the queue.\n"
            "🔊 **!volume** – Adjust the warmth of the sound.\n"
            "🔀 **!shuffle** – Let the winds of chance guide your queue.\n"
            "📜 **!queue** – Peek at the journey ahead with a scrollable playlist."
        ),
        inline=False
    )

    embed.add_field(
        name="📂 Uploads & Playback – Curate your cozy corner",
        value=(
            "📁 **!listsongs** – Explore your uploaded treasures with filters, tags, and more.\n"
            "🔢 **!playbynumber** – Play specific songs by their number.\n"
            "📄 **!playbypage** – Queue entire pages of uploads in one go.\n"
            "🌎 **!playalluploads** – Let every note shine by queuing them all (shuffled).\n"
            "❌ **!removeupload** – Gently retire a song from your collection.\n"
            "🧹 **!clearuploads** – Clear the canvas for new creations."
        ),
        inline=False
    )

    embed.add_field(
        name="🏷️ Tagging System – Organize with heart",
        value=(
            "🔖 **!tag** – Add tags to your uploads like 'chill', 'sunset', or 'vibe'.\n"
            "💚 **!playbytag** – Queue everything with a matching heartbeat.\n"
            "📑 **!listtags** – See the beautiful constellation of tags you've created."
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️ Utility – Stay connected with ease",
        value=(
            "🔗 **!join** – Invite Echosol to your voice channel with a smile.\n"
            "🚪 **!leave** – Let the bot float back into the light.\n"
            "🧺 **!clearqueue** – Empty the queue and start fresh.\n"
            "💡 **!help** – You're never alone – revisit this guide anytime."
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

    # Let the sunshine flow through commands 🌤
    await bot.process_commands(message)

    # Skip if the message is from another bot
    if message.author.bot:
        return

    # Handle song uploads with warmth 🎶
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
                f"🌟 Thank you for sharing your musical light! 🌈\n"
                f"🎵 Uploaded: **{', '.join(new_files)}**\n"
                f"💫 Please reply to this message with tags (like `chill`, `sunset`, `epic`). Separate with spaces or commas!"
            )
        return

    # Handle tag replies with gentle guidance 💖
    if message.reference and message.author.id in pending_tag_uploads:
        tags = [t.strip().lower() for t in message.content.replace(",", " ").split()]
        if not tags:
            await message.channel.send("⚠️ Oops! No tags found. Try again with some beautiful labels 🌻")
            return

        for filename in pending_tag_uploads[message.author.id]:
            if filename not in file_tags:
                file_tags[filename] = []
            file_tags[filename].extend(tags)

        await message.channel.send(
            f"🏷️ Your sound sparkles have been tagged! ✨\n"
            f"💖 Tagged **{len(pending_tag_uploads[message.author.id])}** file(s) with: `{', '.join(tags)}`"
        )

        del pending_tag_uploads[message.author.id]

@bot.command(aliases=["playwithme", "connect", "verbinden"])
async def join(ctx):
    """Joins a voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("💫 Echosol has joined you in song and spirit!")
    else:
        await ctx.send("❌ Echosol cannot find your spirit... Join a voice channel first!")

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
    """Plays a song from YouTube or adds it to the queue with warmth 🌞"""
    if not url:
        await ctx.send("☀️ Please share a YouTube link so we can light up the vibes!")
        return

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await ctx.send("🎧 Joined your voice channel, ready to share the light!")
        else:
            await ctx.send("💭 Hop into a voice channel and summon me with sunshine!")
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
                await ctx.send(f"📀 Added **{added} radiant tunes** from the playlist to the journey!")
            else:  # Single video
                song_queue.append((info['webpage_url'], info['title']))
                await ctx.send(f"🌻 **{info['title']}** has been added to the soundscape!")

    except Exception as e:
        await ctx.send(f"⚠️ A cloud blocked the song: `{e}`")
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
            
            if audio and audio.info:
                duration = int(audio.info.length)
            else:
                duration = 0
        except Exception:
            print(f"[Warning] Could not read duration for: {song_url}")
            duration = 0

        vc = ctx.voice_client

        def after_play(error):
            if error:
                print(f"⚠️ Playback error: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        vc.play(discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS), after=after_play)
        vc.source = discord.PCMVolumeTransformer(vc.source, volume_level)

        # Heartbeats of light bar
        def heartbeats_bar(current, total, segments=10):
            filled = int((current / total) * segments)
            bar = ""
            for i in range(segments):
                if i < filled:
                    bar += "💛"
                elif i == filled:
                    bar += "💖"
                else:
                    bar += "🤍"
            return bar

        # Format time for display
        def format_time(seconds):
            return f"{seconds // 60}:{seconds % 60:02d}"

        embed = discord.Embed(
            title="🌞 Echosol Radiance",
            description=f"✨ **{song_title}** is glowing through your speakers!",
            color=discord.Color.from_str("#ffc0cb")
        )

        if duration:
            embed.add_field(name="Progress", value=f"{heartbeats_bar(0, duration)} `0:00 / {format_time(duration)}`", inline=False)
        message = await ctx.send(embed=embed)

        # Progress bar loop
        if duration:
            for second in range(1, duration + 1):
                bar = heartbeats_bar(second, duration)
                timestamp = f"{format_time(second)} / {format_time(duration)}"
                try:
                    embed.set_field_at(0, name="Progress", value=f"{bar} `{timestamp}`", inline=False)
                    await message.edit(embed=embed)
                except discord.HTTPException:
                    pass
                await asyncio.sleep(1)
        else:
            await message.edit(content=f"▶️ Now playing: **{song_title}**")
    else:
        await ctx.send("🌈 The musical journey is paused, but the stage awaits. ✨ Use `!play` when you're ready to glow again!")

@bot.command(aliases=["mixitup", "mischen", "shuff"])
async def shuffle(ctx):
    """Shuffles the current music queue with joy 🌻"""
    if len(song_queue) > 1:
        random.shuffle(song_queue)
        await ctx.send("🔀 The playlist has been spun like sunrays through stained glass. 🌞")
    else:
        await ctx.send("🌱 Not quite enough tunes to dance with. Add more and try again!")

@bot.command(aliases=["hush"])
async def pause(ctx):
    """Pauses the current song with a gentle hush 🌙"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("💤 A gentle pause... the music takes a breath beneath the stars.")

@bot.command(aliases=["youmayspeak"])
async def resume(ctx):
    """Resumes paused music with heart 💖"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("💓 The melody awakens — your rhythm pulses with light once more!")

@bot.command(aliases=["nextplease", "skippy"])
async def skip(ctx):
    """Skips the current song with a gleam 💫"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await play_next(ctx)
        await ctx.send("⏭ Onward to the next harmony in your journey of sound 🌟")

@bot.command(aliases=["turnitup", "tooloud", "v"])
async def volume(ctx, volume: int):
    """Sets the bot's volume like turning up the sun ☀️"""
    global volume_level
    if 1 <= volume <= 100:
        volume_level = volume / 100.0
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume_level
        await ctx.send(f"🔊 Volume tuned to **{volume}%** — let your light shine brighter!")
    else:
        await ctx.send("🚫 Volume must be between **1 and 100** — just like sunshine, too much can burn! 🌞")

@bot.command(aliases=["whatsnext", "q"])
async def queue(ctx):
    """Displays the current queue with pagination and a shuffle button."""
    if not song_queue:
        await ctx.send("🌥️ The queue is empty... add a little sunshine with `!play`, `!listsongs`, or more!")
        return

    class QueuePages(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.page = 0
            self.items_per_page = 10

        async def send_page(self, interaction=None, message=None):
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            page_items = song_queue[start:end]

            queue_display = '\n'.join([
                f"{i+1}. {os.path.basename(song[1]) if isinstance(song, tuple) else os.path.basename(song)}"
                for i, song in enumerate(page_items, start=start)
            ])

            embed = discord.Embed(
                title=f"🌞 Echosol Queue — Page {self.page + 1}",
                description=queue_display or "🌤️ This page is feeling a little empty...",
                color=discord.Color.from_str("#f9c6eb")
            )
            embed.set_footer(text="Use the buttons below to navigate or shuffle ✨")

            if interaction:
                await interaction.response.edit_message(embed=embed, view=self)
            elif message:
                await message.edit(embed=embed, view=self)

        @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.blurple)
        async def prev_page(self, interaction: discord.Interaction, button: Button):
            if self.page > 0:
                self.page -= 1
                await self.send_page(interaction)

        @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.blurple)
        async def next_page(self, interaction: discord.Interaction, button: Button):
            max_pages = (len(song_queue) - 1) // self.items_per_page
            if self.page < max_pages:
                self.page += 1
                await self.send_page(interaction)

        @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.green)
        async def shuffle_queue(self, interaction: discord.Interaction, button: Button):
            random.shuffle(song_queue)
            self.page = 0
            await interaction.response.send_message("🔀 The queue was kissed by the wind and reshuffled!", ephemeral=True)
            await self.send_page(interaction)

    view = QueuePages()
    start = 0
    end = start + view.items_per_page
    page_items = song_queue[start:end]
    queue_display = '\n'.join([
        f"{i+1}. {os.path.basename(song[1]) if isinstance(song, tuple) else os.path.basename(song)}"
        for i, song in enumerate(page_items, start=start)
    ])

    embed = discord.Embed(
        title="🌞 Echosol Queue — Page 1",
        description=queue_display or "🌤️ This page is feeling a little empty...",
        color=discord.Color.from_str("#f9c6eb")
    )
    embed.set_footer(text="Use the buttons below to navigate or shuffle ✨")
    await ctx.send(embed=embed, view=view)

from discord.ui import View, Button, Select
import math

@bot.command(aliases=["whatwegot"])
async def listsongs(ctx):
    """Lists available uploaded songs with optional tag filter, pagination, and actions."""
    if not uploaded_files:
        await ctx.send("🌥️ No sunshine yet! Upload a song to brighten the playlist.")
        return

    per_page = 10
    range_size = 25
    all_tags = sorted(set(tag for tags in file_tags.values() for tag in tags))

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
        title = "🌼 Radiant Uploads"
        if state.selected_tag:
            title += f" – Tag: {state.selected_tag}"

        embed = discord.Embed(
            title=title + f" (Page {state.current_page + 1}/{total_pages})",
            description=song_list or "☁️ This page is a little quiet...",
            color=discord.Color.from_str("#f9c6eb")  # Soft pink heartlight
        )
        embed.set_footer(text="✨ Let your playlist bloom. Use !playnumber or the buttons below.")
        return embed

    class TagSelector(Select):
        def __init__(self):
            options = [discord.SelectOption(label="🌈 All Songs", value="all")] + [
                discord.SelectOption(label=tag, value=tag) for tag in all_tags
            ]
            super().__init__(placeholder="🎨 Filter by tag...", options=options)

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
            await interaction.response.send_message(
                f"💖 You queued {len(added)} joyful tunes from this page!",
                ephemeral=True
            )
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
            await interaction.response.send_message(
                f"🌟 Shuffled and queued {len(added)} sparkling songs!",
                ephemeral=True
            )
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
        await ctx.send("🌥️ No musical sunshine found! Upload a song to brighten the day.")
        return

    # Shuffle a copy of the uploaded file list
    shuffled_songs = uploaded_files[:]
    random.shuffle(shuffled_songs)

    # Queue them
    for filename in shuffled_songs:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue.append(song_path)

    await ctx.send(f"🌈 A radiant mix of **{len(shuffled_songs)}** uploaded songs has been queued! Let the light flow 🎶")

    # Connect and start playing
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await ctx.send("🌟 Echosol has joined your voice channel to begin the musical journey!")
        else:
            await ctx.send("❌ You need to be in a voice channel to share the light!")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["deleteit", "deleteupload", "ru"])
async def removeupload(ctx, number: int):
    """Removes a specific uploaded song by its number (from !listsongs)."""
    if number < 1 or number > len(uploaded_files):
        await ctx.send("🌧️ That number doesn’t shine. Use `!listsongs` to find your musical stars.")
        return

    filename = uploaded_files[number - 1]
    file_path = os.path.join(MUSIC_FOLDER, filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            uploaded_files.remove(filename)
            if filename in file_tags:
                del file_tags[filename]  # Also remove associated tags if present
            await ctx.send(f"💨 **{filename}** has floated away on a gentle breeze. One less note in the skies.")
        else:
            await ctx.send("⚠️ That file seems to have already drifted into the clouds...")
    except Exception as e:
        await ctx.send(f"💔 Oh no! I couldn't let it go: `{e}`")

@bot.command(aliases=["pp", "seite", "page", "playpage"])
async def playbypage(ctx, *pages):
    """Plays one or more pages of uploaded songs."""
    per_page = 10
    total_pages = (len(uploaded_files) + per_page - 1) // per_page
    added = []

    if not pages:
        await ctx.send("🌻 Please share one or more page numbers to bring the sunshine! (e.g. `!page 1 2 3`)")
        return

    for page_str in pages:
        try:
            page = int(page_str)
            if page < 1 or page > total_pages:
                await ctx.send(f"⚠️ Page {page} is out of range and couldn’t catch the breeze. Skipping.")
                continue

            start = (page - 1) * per_page
            end = start + per_page
            for filename in uploaded_files[start:end]:
                song_path = os.path.join(MUSIC_FOLDER, filename)
                song_queue.append(song_path)
                added.append(filename)
        except ValueError:
            await ctx.send(f"🌥️ `{page_str}` isn’t a valid number. Let’s float past it.")

    if not added:
        await ctx.send("❌ No songs danced into the queue. Try again with valid pages.")
        return

    await ctx.send(f"🎶✨ Added **{len(added)}** radiant tracks from page(s) {', '.join(pages)} to your musical journey!")

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("🌙 You need to be in a voice channel to let the melodies flow.")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["number", "playnumber", "n"])
async def playbynumber(ctx, *numbers):
    """Plays one or multiple uploaded songs using their numbers."""
    added_songs = []

    if not numbers:
        await ctx.send("❌ Please provide one or more song numbers. Example: `!playbynumber 1 2 3`")
        return

    for num in numbers:
        try:
            num = int(num.strip(','))  # Clean and convert to int
            if 1 <= num <= len(uploaded_files):
                song_path = os.path.join(MUSIC_FOLDER, uploaded_files[num - 1])
                song_queue.append(song_path)
                added_songs.append(uploaded_files[num - 1])
            else:
                await ctx.send(f"⚠️ Song number `{num}` is out of bounds. Use `!listsongs` to see available tracks.")
        except ValueError:
            await ctx.send(f"❌ `{num}` isn't a valid number. Use spaces or commas to separate multiple.")

    if not added_songs:
        await ctx.send("🌧️ No songs were added to the queue... let's try again with some sunshine.")
        return

    await ctx.send(f"🌟 Added to the queue: **{', '.join(added_songs)}** — let the light flow!")

    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to hear the glow of music!")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["flag", "etikett"])
async def tag(ctx, *args):
    """Tags one or more uploaded songs. Usage: !tag <number(s)> <tags...>"""
    if len(args) < 2:
        await ctx.send("🌻 To blossom your tunes with tags, use: `!tag <song number(s)> <tags>`\nExample: `!tag 1 2 chill vibe`")
        return

    try:
        # Split numbers and tags
        numbers = [int(arg) for arg in args if arg.isdigit()]
        tags = [arg.lower() for arg in args if not arg.isdigit()]
    except ValueError:
        await ctx.send("⚠️ Hmm, some of those song numbers didn’t look quite right. Please only use numbers for the songs.")
        return

    if not numbers or not tags:
        await ctx.send("🌸 Please give me both the song numbers *and* the beautiful tags you'd like to add.")
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
            await ctx.send(f"🌥️ Skipped song number {num} – it's not in our garden of uploads!")

    if tagged:
        await ctx.send(f"🏷️✨ Songs kissed by sunshine: {', '.join(tagged)}\nWith glowing tags: `{', '.join(tags)}`")
    else:
        await ctx.send("☁️ No songs were tagged this time. Try again with different numbers or tags!")

@bot.command(aliases=["tagplay", "greenflag"])
async def playbytag(ctx, *search_tags):
    """Plays all uploaded songs that match one or more tags. Usage: !playbytag chill vibe"""
    if not search_tags:
        await ctx.send("🌿 Please share at least one tag to guide the vibe. Example: `!playbytag chill`")
        return

    tags_lower = [t.lower() for t in search_tags]
    matched = [f for f in uploaded_files if any(tag in file_tags.get(f, []) for tag in tags_lower)]

    if not matched:
        await ctx.send(f"☁️ No songs found glowing with tag(s): `{', '.join(tags_lower)}`. Try another gentle whisper?")
        return

    # Add matched songs to the queue
    for filename in matched:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue.append(song_path)

    await ctx.send(f"🌈 Added **{len(matched)}** radiant tracks to the queue, inspired by tag(s): `{', '.join(tags_lower)}` ✨")

    # Auto-play if nothing is currently playing
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You need to be in a voice channel to let the music shine through.")
            return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["whiteflag", "viewtags", "showtags"])
async def listtags(ctx):
    """Shows all tags currently in use for uploaded songs."""
    if not file_tags:
        await ctx.send("🌥️ No tags have been shared with the universe yet.")
        return

    # Collect all unique tags
    unique_tags = set()
    for tags in file_tags.values():
        unique_tags.update(tags)

    if not unique_tags:
        await ctx.send("🌫️ The air is still—no tags are dancing right now.")
        return

    sorted_tags = sorted(unique_tags)
    tag_text = ", ".join(sorted_tags)

    embed = discord.Embed(
        title="🌼 Tags Blooming in the Archive",
        description=f"`{tag_text}`",
        color=discord.Color.from_str("#ffb6c1")  # Soft pink like morning light
    )
    embed.set_footer(text="Tag your uploads to help them shine brighter ✨")

    await ctx.send(embed=embed)

@bot.command(aliases=["shutup", "nomore", "stoppen"])
async def stop(ctx):
    """Stops playback and clears the queue."""
    global song_queue
    song_queue.clear()  # Clear the queue

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("🌤️ Echosol takes a gentle breath... The melody has hushed, and your queue has floated away on a breeze. 🍃💛")
    else:
        await ctx.send("🕊️ The air is quiet already, but your queue has been lovingly cleared. 💫")

@bot.command(aliases=["spankies", "cq"])
async def clearqueue(ctx):
    """Clears the music queue."""
    global song_queue
    song_queue = []  # Empty the queue
    await ctx.send("🌈 The queue has been cleared with care — a fresh breeze of musical sunshine awaits. 💛")

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
    await ctx.send(f"🌤️ Echosol has gently released **{file_count}** uploaded songs into the wind. The sky is clear for fresh melodies to shine. 💫")

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
bot.run(TOKEN)