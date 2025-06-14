import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import math
import json
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from discord.ui import View, Select, Button
from discord import Interaction
from datetime import datetime

# Load environment variables (Ensure TOKEN is stored in Railway Variables or .env file)
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Allow the bot to track server members (including itself)

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

def get_current_form():
    now = datetime.utcnow()

@bot.command(aliases=["lost", "helfen"])
async def help(ctx):
    """Displays all main commands with dropdown selection."""
    class HelpDropdown(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="🌞 Playback", description="Commands for music control."),
                discord.SelectOption(label="📂 Uploads", description="Manage uploaded songs."),
                discord.SelectOption(label="🏷️ Tagging System", description="Tag and find songs by vibe."),
                discord.SelectOption(label="🛠️ Utility", description="General bot functions.")
            ]
            super().__init__(placeholder="Choose a category to explore...", options=options)

        async def callback(self, interaction: Interaction):
            choice = self.values[0]

            embed = discord.Embed(
                color=discord.Color.from_str("#ffe680"),
                title="✨ Echosol Help – Glowing Commands Guide"
            )
            embed.set_footer(text="🌻 Let the sunshine guide your musical path.")

            if "Playback" in choice:
                embed.title = "🌞 Playback – Light up the room!"
                embed.description = (
                    "🎶 **!play** – Bring in a melody from YouTube. Alias: p\n"
                    "⏸️ **!pause** – Pause the radiant rhythm\n"
                    "▶️ **!resume** – Resume your beam of sound\n"
                    "⏭️ **!skip** – Skip to the next shining note\n"
                    "⏹️ **!stop** – Bring the music to a gentle halt & clear the queue\n"
                    "🔊 **!volume** – Adjust the warmth of sound. Alias: v\n"
                    "🔀 **!shuffle** – Let the winds of chance guide your queue.\n"
                    "📜 **!queue** – View the glowing journey ahead. Alias: q"
                )
            elif "Uploads" in choice:
                embed.title = "📂 Uploads – Curate your cozy corner"
                embed.description = (
                    "📁 **!listsongs** – Explore uploaded treasures\n"
                    "🔢 **!playbynumber** – Choose your glow by number. Alias: n\n"
                    "📄 **!playbypage** – Tune into pages of your musical journey. Alias: pp\n"
                    "🌎 **!playalluploads** – Let every note shine at once - mixed with magic.\n"
                    "❌ **!deleteupload** – Tuck a song away to make room for more stars. Alias: du\n"
                    "🧹 **!clearuploads** – Sweep the canvas clean for new creations. Alias: cu"
                )
            elif "Tagging" in choice:
                embed.title = "🏷️ Tagging System – Organize with heart"
                embed.description = (
                    "🔖 **!tag** – Let your songs blossom with custom tags like 'sunrise', 'cozy', or 'adventure'.\n"
                    "💚 **!playbytag** – Play all songs sharing the same spark of light.\n"
                    "📑 **!listtags** – See the beautiful constellation of tags you've created."
                    "🌿 **!removetag** – Breeze away a tag or free songs from all their labels. Alias: untag."
                )
            elif "Utility" in choice:
                embed.title = "🛠️ Utility – Stay connected with ease"
                embed.description = (
                    "🔗 **!join** – Call down a beam of warmth — Echosol arrives, heart first.\n"
                    "🚪 **!leave** – Let the light return to the stars\n"
                    "🧺 **!clearqueue** – Empty the queue and start fresh. Alias: cq\n"
                    "💡 **!help** – You're never alone – revisit this guide anytime."
                )

            await interaction.response.edit_message(embed=embed, view=view)

    class HelpView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.add_item(HelpDropdown())

    intro_embed = discord.Embed(
        title="✨ Welcome to Echosol, your heart's musical companion 💖",
        description="Let the rhythm guide your soul and the light lead your playlist 🌈🎵",
        color=discord.Color.from_str("#ffe680")
    )
    intro_embed.set_footer(text="🌻 Echosol is powered by light, rhythm, and you – your musical journey starts here.")

    view = HelpView()
    await ctx.send(embed=intro_embed, view=view)

# Configure YouTube downloader settings
YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    },
}

FFMPEG_OPTIONS = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}
FFMPEG_LOCAL_OPTIONS = {
    'before_options': '-nostdin',
    'options': '-vn'
}

from collections import defaultdict
usage_counters = defaultdict(int)
pending_tag_uploads = defaultdict(dict)  # {guild_id: {user_id: [filenames]}}
file_tags_by_guild = defaultdict(dict)
uploaded_files_by_guild = defaultdict(list)
song_queue_by_guild = defaultdict(list)
last_now_playing_message_by_guild = defaultdict(lambda: None)
volume_levels_by_guild = defaultdict(lambda: 1.0)

SAVE_FILE = "uploads_data.json"

def save_upload_data():
    try:
        data = {
            "uploaded_files_by_guild": uploaded_files_by_guild,
            "file_tags_by_guild": file_tags_by_guild,
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[Save Error] Could not save upload data: {e}")

def load_upload_data():
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            for guild_id, files in data.get("uploaded_files_by_guild", {}).items():
                uploaded_files_by_guild[int(guild_id)] = files
            for guild_id, tags in data.get("file_tags_by_guild", {}).items():
                file_tags_by_guild[int(guild_id)] = tags
        print("[Startup] Upload data loaded successfully.")
    except FileNotFoundError:
        print("[Startup] No saved upload data found. Starting fresh.")
    except Exception as e:
        print(f"[Load Error] Could not load upload data: {e}")

load_upload_data()

@bot.event
async def on_message(message):
    # Let the sunshine flow through commands 🌤
    await bot.process_commands(message)

    # Skip if the message is from another bot or not in a guild
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    user_id = message.author.id

    # Handle song uploads with warmth 🎶
    if message.attachments:
        new_files = []
        for attachment in message.attachments:
            if attachment.filename.endswith(('.mp3', '.wav')):
                file_path = os.path.join(MUSIC_FOLDER, attachment.filename)
                await attachment.save(file_path)
                uploaded_files_by_guild[guild_id].append(attachment.filename)
                new_files.append(attachment.filename)

        if new_files:
            pending_tag_uploads[guild_id][user_id] = new_files
            await message.channel.send(
                f"🌟 Thank you for sharing your musical light! 🌈\n"
                f"🎵 Uploaded: **{', '.join(new_files)}**\n"
                f"💫 Please reply to this message with tags (like `chill`, `sunset`, `epic`). Separate with spaces or commas!"
            )
            save_upload_data()  # ✅ Save after uploading
        return

    # Handle tag replies with gentle guidance 💖
    if message.reference and user_id in pending_tag_uploads[guild_id]:
        try:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return  # Ignore if the message can't be fetched

        # Only accept replies to bot's upload message
        if replied_message.author.id != bot.user.id or not replied_message.content.startswith("🌟 Thank you for sharing your musical light!"):
            return

        tags = [t.strip().lower() for t in message.content.replace(",", " ").split()]
        if not tags:
            await message.channel.send("⚠️ Oops! No tags found. Try again with some beautiful labels 🌻")
            return

        for filename in pending_tag_uploads[guild_id][user_id]:
            if filename not in file_tags_by_guild[guild_id]:
                file_tags_by_guild[guild_id][filename] = []
            file_tags_by_guild[guild_id][filename].extend(tags)

        await message.channel.send(
            f"🏷️ Your sound sparkles have been tagged! ✨\n"
            f"💖 Tagged **{len(pending_tag_uploads[guild_id][user_id])}** file(s) with: `{', '.join(tags)}`"
        )

        del pending_tag_uploads[guild_id][user_id]
        save_upload_data()  # ✅ Save after tagging

@bot.command(aliases=["playwithme", "connect", "verbinden", "kisses"])
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
    """Leaves the voice channel with gentle farewell."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🌅 Echosol has gently drifted from the voice channel, returning to the cosmos. 💫")
    else:
        await ctx.send("🌙 I'm not shining in any voice channel right now.")

@bot.command(aliases=["p", "gimme", "spielen"])
async def play(ctx, url: str = None):
    """Plays a song from YouTube or adds it to the queue with warmth 🌞"""
    guild_id = ctx.guild.id

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
                        song_queue_by_guild[guild_id].append((entry_info['webpage_url'], entry_info['title']))
                        added += 1
                await ctx.send(f"📀 Added **{added} radiant tunes** from the playlist to the journey!")
            else:  # Single video
                song_queue_by_guild[guild_id].append((info['webpage_url'], info['title']))
                await ctx.send(f"🌻 **{info['title']}** has been added to the soundscape!")

    except Exception as e:
        await ctx.send(f"⚠️ A cloud blocked the song: `{e}`")
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if vc and vc.is_playing():
        return

    if not song_queue_by_guild[guild_id]:
        await ctx.send("🌈 The musical journey is paused, but the stage awaits. ✨ Use `!play` when you're ready to glow again!")
        return

    # Mark guild activity
    usage_counters[guild_id] += 1
    is_high_usage = usage_counters[guild_id] >= 30

    # Clean up old embed if any
    if last_now_playing_message_by_guild.get(guild_id):
        try:
            embed = last_now_playing_message_by_guild[guild_id].embeds[0]
            embed.set_field_at(0, name="Progress", value="💤 This song has finished playing. `Complete`", inline=False)
            await last_now_playing_message_by_guild[guild_id].edit(embed=embed)
        except Exception:
            pass
        last_now_playing_message_by_guild[guild_id] = None

    # Get next song
    song_data = song_queue_by_guild[guild_id].pop(0)
    is_temp_youtube = False

    # Download or load audio
    if isinstance(song_data, tuple):
        original_url, song_title = song_data
        try:
            with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(original_url, download=True)
                song_url = info['requested_downloads'][0]['filepath'] if 'requested_downloads' in info else ydl.prepare_filename(info)
                duration = info.get('duration', 0)
                is_temp_youtube = True
        except Exception as e:
            await ctx.send(f"⚠️ Could not fetch audio: {e}\nSkipping to next song...")
            return await play_next(ctx)
        ffmpeg_options = FFMPEG_LOCAL_OPTIONS
    else:
        song_url = song_data
        song_title = os.path.basename(song_url)
        try:
            audio = MP3(song_url) if song_url.endswith(".mp3") else WAVE(song_url)
            duration = int(audio.info.length) if audio and audio.info else 0
        except Exception:
            duration = 0
        ffmpeg_options = FFMPEG_LOCAL_OPTIONS

    # Handle cleanup after song finishes
    def after_play(error):
        if error:
            print(f"⚠️ Playback error: {error}")
        if is_temp_youtube and os.path.exists(song_url):
            try:
                os.remove(song_url)
            except Exception as e:
                print(f"[Cleanup Error] Could not delete file: {e}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    # Start playing
    vc.play(discord.FFmpegPCMAudio(song_url, **ffmpeg_options), after=after_play)
    vc.source = discord.PCMVolumeTransformer(vc.source, volume_levels_by_guild[guild_id])

    # Seasonal system starts here
    from datetime import datetime

    def get_current_form():
        now = datetime.utcnow()
        month = now.month
        day = now.day
        if (month == 3 and day >= 21) or (month == 4):
            return "vernalight"
        elif (month == 6 and day >= 21) or (month == 7):
            return "solshine"
        elif (month == 9 and day >= 21) or (month == 10):
            return "fallchord"
        elif (month == 12 and day >= 21) or (month == 1):
            return "frostveil"
        else:
            return "default"

    SEASONAL_FORMS = {
        "vernalight": {
            "name": "🌸 Vernalight Blossoms",
            "color": 0xB3C7F9,
            "bar_emojis": ['🌧️', '☔', '💧', '💮']
        },
        "solshine": {
            "name": "🌞 Solshine Radiance",
            "color": 0xFFD966,
            "bar_emojis": ['☀️', '🌻', '🌼', '✨']
        },
        "fallchord": {
            "name": "🍂 Fallchord Resonance",
            "color": 0xFF9933,
            "bar_emojis": ['🍁', '🍂', '🦇', '🎃']
        },
        "frostveil": {
            "name": "❄️ Frostveil Stillness",
            "color": 0x99CCFF,
            "bar_emojis": ['❄️', '💙', '🌨️', '🧊']
        },
        "default": {
            "name": "🎵 Echosol Harmonies",
            "color": 0xFFDB8A,
            "bar_emojis": [
                '<:echo2:1383471283076862037>',
                '<:echo1:1383471280694497391>',
                '<:echo4:1383471288500097065>',
                '<:echo3:1383471285123813507>'
            ]
        }
    }

    current_form = get_current_form()
    form_data = SEASONAL_FORMS.get(current_form, SEASONAL_FORMS["default"])

    # Progress bar generator
    def seasonal_progress_bar(current, total, segments=10, pulse_state=0):
        filled = int((current / total) * segments)
        emojis = form_data["bar_emojis"]
        pulse = emojis[pulse_state % len(emojis)]
        return ''.join(emojis[0] if i < filled else pulse if i == filled else "▫️" for i in range(segments))

    progress_bar_func = seasonal_progress_bar

    # Initial embed
    embed = discord.Embed(
        title=form_data["name"],
        description=f"🎶 **{song_title}** is playing!",
        color=form_data["color"]
    )

    if duration:
        embed.add_field(name="Progress", value=f"{progress_bar_func(0, duration)} `0:00 / {duration // 60}:{duration % 60:02d}`", inline=False)

    message = await ctx.send(embed=embed)
    last_now_playing_message_by_guild[guild_id] = message

    # Update progress loop
    if duration and not is_high_usage:
        for second in range(1, duration + 1):
            bar = progress_bar_func(second, duration, pulse_state=second)
            timestamp = f"{second // 60}:{second % 60:02d} / {duration // 60}:{duration % 60:02d}"

            if second % 5 == 0 or second == duration:
                try:
                    embed.set_field_at(0, name="Progress", value=f"{bar} `{timestamp}`", inline=False)
                    await message.edit(embed=embed)
                except discord.HTTPException:
                    pass

            await asyncio.sleep(1)

        # Finale phase
        try:
            embed.title = "🌟 Finale Glow"
            embed.description = f"**{song_title}** just wrapped its dance of light!"
            embed.set_field_at(0, name="Progress", value="✨✨✨✨✨✨✨✨✨✨ `Finished`", inline=False)
            await message.edit(embed=embed)
        except discord.HTTPException:
            pass

        await asyncio.sleep(6)

        try:
            embed.set_field_at(0, name="Progress", value="🌙 The glow fades gently... `Complete`", inline=False)
            await message.edit(embed=embed)
        except discord.HTTPException:
            pass
    else:
        await message.edit(content=f"▶️ Now playing: **{song_title}**")

@bot.command(aliases=["mixitup", "mischen", "shuff"])
async def shuffle(ctx):
    """Shuffles the current music queue with joy 🌻"""
    guild_id = ctx.guild.id
    queue = song_queue_by_guild.get(guild_id, [])
    if len(queue) > 1:
        random.shuffle(queue)
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

@bot.command(aliases=["nextplease", "next", "skippy"])
async def skip(ctx):
    """Skips the current song with a gleam 💫"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await play_next(ctx)
        await ctx.send("⏭ Onward to the next harmony in your journey of sound 🌟")

@bot.command(aliases=["turnitup", "tooloud", "v"])
async def volume(ctx, volume: int):
    """Sets the bot's volume like turning up the sun ☀️"""
    guild_id = ctx.guild.id

    if 1 <= volume <= 100:
        volume_levels_by_guild[guild_id] = volume / 100.0

        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume_levels_by_guild[guild_id]

        await ctx.send(f"🔊 Volume tuned to **{volume}%** — let your light shine brighter!")
    else:
        await ctx.send("🚫 Volume must be between **1 and 100** — just like sunshine, too much can burn! 🌞")

@bot.command(aliases=["whatsnext", "q"])
async def queue(ctx):
    """Displays the current queue with pagination and a shuffle button."""
    guild_id = ctx.guild.id

    if not song_queue_by_guild[guild_id]:
        await ctx.send("🌥️ The queue is empty... add a little sunshine with `!play`, `!listsongs`, or more!")
        return

    class QueuePages(View):
        def __init__(self, guild_id):
            super().__init__(timeout=60)
            self.guild_id = guild_id
            self.page = 0
            self.items_per_page = 10

        async def send_page(self, interaction=None, message=None):
            queue = song_queue_by_guild[self.guild_id]
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            page_items = queue[start:end]

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
            queue = song_queue_by_guild[self.guild_id]
            max_pages = (len(queue) - 1) // self.items_per_page
            if self.page < max_pages:
                self.page += 1
                await self.send_page(interaction)

        @discord.ui.button(label="🔀 Shuffle", style=discord.ButtonStyle.green)
        async def shuffle_queue(self, interaction: discord.Interaction, button: Button):
            queue = song_queue_by_guild[self.guild_id]
            random.shuffle(queue)
            self.page = 0
            await interaction.response.send_message("🔀 The queue was kissed by the wind and reshuffled!", ephemeral=True)
            await self.send_page(interaction)

    view = QueuePages(guild_id)
    await view.send_page(message=await ctx.send(view=view))

@bot.command(aliases=["whatwegot"])
async def listsongs(ctx):
    """Lists available uploaded songs with optional tag filter, pagination, and actions."""
    guild_id = ctx.guild.id

    if not uploaded_files_by_guild[guild_id]:
        await ctx.send("🌥️ No sunshine yet! Upload a song to brighten the playlist.")
        return

    per_page = 10
    range_size = 25

    class State:
        def __init__(self):
            self.current_page = 0
            self.page_range_index = 0
            self.filtered_files = uploaded_files_by_guild[guild_id][:]
            self.selected_tag = None

    state = State()

    def get_page_embed():
        uploaded_files = uploaded_files_by_guild[guild_id]
        file_tags = file_tags_by_guild[guild_id]

        start = state.current_page * per_page
        end = start + per_page
        page = state.filtered_files[start:end]

        song_list = ""
        for i, song in enumerate(page):
            song_list += f"{start + i + 1}. {song}\n"

        total_pages = max(1, math.ceil(len(state.filtered_files) / per_page))
        title = "🌼 Radiant Uploads"
        if state.selected_tag:
            title += f" – Tag: {state.selected_tag}"

        embed = discord.Embed(
            title=f"{title} (Page {state.current_page + 1}/{total_pages})",
            description=song_list or "☁️ This page is a little quiet...",
            color=discord.Color.from_str("#f9c6eb")
        )
        embed.set_footer(text="✨ Let your playlist bloom. Use !playnumber or the buttons below.")
        return embed

    class TagSelector(Select):
        def __init__(self):
            file_tags = file_tags_by_guild[guild_id]
            all_tags = sorted(set(tag for tags in file_tags.values() for tag in tags))
            options = [discord.SelectOption(label="🌈 All Songs", value="all")] + [
                discord.SelectOption(label=tag, value=tag) for tag in all_tags
            ]
            super().__init__(placeholder="🎨 Filter by tag...", options=options)

        async def callback(self, interaction: discord.Interaction):
            file_tags = file_tags_by_guild[guild_id]
            uploaded_files = uploaded_files_by_guild[guild_id]

            choice = self.values[0]
            state.selected_tag = None if choice == "all" else choice
            state.current_page = 0
            state.page_range_index = 0

            if state.selected_tag:
                state.filtered_files = [f for f in uploaded_files if state.selected_tag in file_tags.get(f, [])]
            else:
                state.filtered_files = uploaded_files[:]

            await interaction.response.edit_message(embed=get_page_embed(), view=view)

    class PaginationView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.add_item(TagSelector())

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
                song_queue_by_guild[guild_id].append(song_path)
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
                song_queue_by_guild[guild_id].append(song_path)
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
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])
    song_queue = song_queue_by_guild.setdefault(guild_id, [])

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

@bot.command(aliases=["pp", "seite", "page", "playpage"])
async def playbypage(ctx, *pages):
    """Plays one or more pages of uploaded songs."""
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])

    if not uploaded_files:
        await ctx.send("🌥️ No sunshine yet! Upload a song to brighten the playlist.")
        return

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
                song_queue_by_guild.setdefault(guild_id, []).append(song_path)
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
    """Plays one or multiple uploaded songs using their numbers (per-server)."""
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])
    song_queue = song_queue_by_guild.setdefault(guild_id, [])

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
    """Tags one or more uploaded songs. Usage: !tag <number(s)> <tags...> (per-server)"""
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])
    file_tags = file_tags_by_guild.setdefault(guild_id, {})

    if len(args) < 2:
        await ctx.send("🌻 To blossom your tunes with tags, use: `!tag <song number(s)> <tags>`\nExample: `!tag 1 2 chill vibe`")
        return

    try:
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
            file_tags.setdefault(filename, [])
            for tag in tags:
                if tag not in file_tags[filename]:
                    file_tags[filename].append(tag)
            tagged.append(filename)
        else:
            await ctx.send(f"🌥️ Skipped song number {num} – it's not in our garden of uploads!")

    if tagged:
        await ctx.send(f"🏷️✨ Songs kissed by sunshine: {', '.join(tagged)}\nWith glowing tags: `{', '.join(tags)}`")
        save_upload_data()  # ✅ Save only if something was tagged
    else:
        await ctx.send("☁️ No songs were tagged this time. Try again with different numbers or tags!")

@bot.command(aliases=["tagplay", "greenflag", "pt"])
async def playbytag(ctx, *search_tags):
    """Plays all uploaded songs that match one or more tags. Usage: !playbytag chill vibe (per-server)"""
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])
    file_tags = file_tags_by_guild.setdefault(guild_id, {})

    if not uploaded_files:
        await ctx.send("🌥️ No uploads yet — add some sunshine first with an upload.")
        return

    if not search_tags:
        await ctx.send("🌿 Please share at least one tag to guide the vibe. Example: `!playbytag chill`")
        return

    tags_lower = [t.lower() for t in search_tags]
    matched = [
        f for f in uploaded_files
        if any(tag in file_tags.get(f, []) for tag in tags_lower)
    ]

    if not matched:
        await ctx.send(f"☁️ No songs found glowing with tag(s): `{', '.join(tags_lower)}`. Try another gentle whisper?")
        return

    for filename in matched:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue_by_guild.setdefault(guild_id, []).append(song_path)

    await ctx.send(f"🌈 Added **{len(matched)}** radiant tracks to the queue, inspired by tag(s): `{', '.join(tags_lower)}` ✨")

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
    """Shows all tags currently in use for uploaded songs (per-server)."""
    guild_id = ctx.guild.id
    file_tags = file_tags_by_guild.setdefault(guild_id, {})

    # Gather all unique tags
    unique_tags = set()
    for tags in file_tags.values():
        unique_tags.update(tags)

    if not unique_tags:
        await ctx.send("🌫️ The air is still—no tags are dancing right now.")
        return

    sorted_tags = sorted(unique_tags)
    tag_text = ", ".join(sorted_tags)

    # Discord embed descriptions cap at 4096 characters
    max_length = 4000  # Leave room for formatting and footer
    if len(tag_text) > max_length:
        # Trim tag text if too long
        trimmed = tag_text[:max_length]
        last_comma = trimmed.rfind(",")
        trimmed = trimmed[:last_comma] + "..."
        description = f"`{trimmed}`\n\n⚠️ Some tags are hidden due to space. Use filters to browse!"
    else:
        description = f"`{tag_text}`"

    embed = discord.Embed(
        title="🌼 Tags Blooming in the Archive",
        description=description,
        color=discord.Color.from_str("#ffb6c1")
    )
    embed.set_footer(text="Tag your uploads to help them shine brighter ✨")

    await ctx.send(embed=embed)

@bot.command(aliases=["untag", "deletetag", "cleartags"])
async def removetag(ctx, *args):
    """Removes all tags from specified songs, or removes a specific tag from all songs."""
    guild_id = ctx.guild.id
    file_tags = file_tags_by_guild.setdefault(guild_id, {})
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])

    if not args:
        embed = discord.Embed(
            title="🌸 Oops! Missing Details",
            description="Please use:\n\n"
                        "➔ `!removetag <song number(s)>` to clear all tags from songs.\n"
                        "➔ `!removetag <tag>` to remove a tag from all songs.",
            color=discord.Color.from_str("#ffb6c1")
        )
        await ctx.send(embed=embed)
        return

    loading_message = await ctx.send("✨ Polishing your melodies... One moment, please... 🎵")
    await asyncio.sleep(1)

    did_change = False  # 🔄 Track if we made any updates

    if args[0].isdigit():
        numbers = []
        invalid = []
        for arg in args:
            if arg.isdigit():
                numbers.append(int(arg))
            else:
                invalid.append(arg)

        cleared = []
        for num in numbers:
            if 1 <= num <= len(uploaded_files):
                filename = uploaded_files[num - 1]
                if filename in file_tags and file_tags[filename]:
                    file_tags[filename] = []
                    cleared.append(filename)
                    did_change = True  # ✅ Change detected

        if cleared:
            embed = discord.Embed(
                title="💖 Tags Cleared!",
                description="These songs are now floating freely:\n\n" +
                            "\n".join(f"• {file}" for file in cleared),
                color=discord.Color.from_str("#fff0b3")
            )
            embed.set_footer(text="✨ Fresh, tag-free melodies await.")
        else:
            embed = discord.Embed(
                title="🌥️ No Tags Found",
                description="Those songs were already as free as the breeze! 🌬️",
                color=discord.Color.from_str("#add8e6")
            )

        if invalid:
            embed.add_field(
                name="⚠️ Ignored Inputs",
                value=", ".join(invalid),
                inline=False
            )

        await loading_message.edit(content=None, embed=embed)

    else:
        tag_to_remove = args[0].lower()
        removed_from = []

        for filename, tags in file_tags.items():
            if tag_to_remove in tags:
                tags.remove(tag_to_remove)
                removed_from.append(filename)
                did_change = True  # ✅ Change detected

        if removed_from:
            embed = discord.Embed(
                title="🏷️ Tag Gently Lifted",
                description=f"Removed `{tag_to_remove}` from these songs:\n\n" +
                            "\n".join(f"• {file}" for file in removed_from),
                color=discord.Color.from_str("#ffd1dc")
            )
            embed.set_footer(text="🌼 Like flowers shedding petals to the wind...")
        else:
            embed = discord.Embed(
                title="🌫️ No Songs Found",
                description=f"No songs were carrying the tag `{tag_to_remove}` 🌙",
                color=discord.Color.from_str("#d3d3f3")
            )

        await loading_message.edit(content=None, embed=embed)

    if did_change:
        save_upload_data()  # ✅ Save only if something changed

@bot.command(aliases=["shutup", "nomore", "stoppen"])
async def stop(ctx):
    """Stops playback and clears the queue."""
    guild_id = ctx.guild.id
    song_queue_by_guild[guild_id] = []

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("🌤️ Echosol takes a gentle breath... The melody has hushed, and your queue has floated away on a breeze. 🍃💛")
    else:
        await ctx.send("🕊️ The air is quiet already, but your queue has been lovingly cleared. 💫")

@bot.command(aliases=["delete", "removeupload", "du", "byebish"])
async def deleteupload(ctx, *numbers):
    """Deletes one or multiple uploaded songs by their numbers (from !listsongs)."""
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])
    file_tags = file_tags_by_guild.get(guild_id, {})

    if not numbers:
        await ctx.send("🌱 Please share the number(s) of the uploaded song(s) to release. Example: `!du 1 2 3`")
        return

    deleted = []
    invalid = []

    for num_str in numbers:
        try:
            num = int(num_str.strip(','))
            if 1 <= num <= len(uploaded_files):
                filename = uploaded_files[num - 1]
                file_path = os.path.join(MUSIC_FOLDER, filename)

                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"[Warning] Could not delete {filename}: {e}")

                deleted.append(filename)
            else:
                invalid.append(num_str)
        except ValueError:
            invalid.append(num_str)

    # Remove deleted entries from memory and tags
    for filename in deleted:
        if filename in uploaded_files:
            uploaded_files.remove(filename)
        if filename in file_tags:
            del file_tags[filename]

    # Update persistent storage
    uploaded_files_by_guild[guild_id] = uploaded_files
    file_tags_by_guild[guild_id] = file_tags
    save_upload_data()

    if deleted:
        await ctx.send(
            f"💫 Released **{len(deleted)}** file(s) into the wind:\n"
            f"✨ `{', '.join(deleted)}`"
        )
    if invalid:
        await ctx.send(
            f"⚠️ These didn’t shimmer quite right and were skipped: `{', '.join(invalid)}`\n"
            "Use `!listsongs` to see the right numbers 🌈"
        )

@bot.command(aliases=["spankies", "cq"])
async def clearqueue(ctx):
    """Clears the music queue for this server only."""
    guild_id = ctx.guild.id
    song_queue_by_guild[guild_id] = []

    await ctx.send("🌈 The queue has been cleared with care — a fresh breeze of musical sunshine awaits. 💛")

@bot.command(aliases=["exterminate", "cu"])
async def clearuploads(ctx):
    """Deletes all uploaded files for this server to free space, with confirmation."""
    guild_id = ctx.guild.id
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])

    if not uploaded_files:
        await ctx.send("🌥️ There's nothing here — your musical skies are already clear.")
        return

    class ConfirmClearView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=15)

        @discord.ui.button(label="✅ Yes, clear all", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("Only the melody master who called this may clear the skies!", ephemeral=True)
                return

            file_count = 0
            for filename in uploaded_files_by_guild[guild_id]:
                file_path = os.path.join(MUSIC_FOLDER, filename)
                if os.path.exists(file_path) and filename.endswith(('.mp3', '.wav')):
                    try:
                        os.remove(file_path)
                        file_count += 1
                    except Exception as e:
                        print(f"[Warning] Failed to delete {filename}: {e}")

            uploaded_files_by_guild[guild_id] = []
            file_tags_by_guild[guild_id] = {}

            save_upload_data()  # ✅ persist the clear!

            await interaction.response.edit_message(content=(
                f"🌤️ Echosol has gently released **{file_count}** uploaded songs into the wind.\n"
                f"The sky is clear for fresh melodies to shine. 💫"
            ), view=None)

        @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == ctx.author:
                await interaction.response.edit_message(content="🌈 The skies remain untouched. No files were harmed. 💛", view=None)
            else:
                await interaction.response.send_message("Only the original summoner can cancel this. 🌟", ephemeral=True)

    await ctx.send(
        "⚠️ Are you sure you want to clear **all uploaded songs** for this server?\n"
        "This action cannot be undone.",
        view=ConfirmClearView()
    )

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
load_upload_data()
bot.run(TOKEN)