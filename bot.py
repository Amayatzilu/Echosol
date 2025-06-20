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

# Main playlist storage
playlists_by_guild = {}
PLAYLISTS_FILE = "playlists.json"

# Load existing playlists

def load_playlists():
    global playlists_by_guild
    if os.path.exists(PLAYLISTS_FILE):
        with open(PLAYLISTS_FILE, "r") as f:
            playlists_by_guild = json.load(f)
    else:
        playlists_by_guild = {}

# Save playlists

def save_playlists():
    with open(PLAYLISTS_FILE, "w") as f:
        json.dump(playlists_by_guild, f, indent=2)

# Ensure every guild has an initialized dict

def ensure_guild_playlists(guild_id):
    guild_id = str(guild_id)
    if guild_id not in playlists_by_guild:
        playlists_by_guild[guild_id] = {}

# Configure YouTube downloader settings
cookies_path = "/app/cookies.txt"
cookie_data = os.getenv("YOUTUBE_COOKIES", "")

if cookie_data:
    with open(cookies_path, "w") as f:
        f.write(cookie_data)

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)  # Disables default help

async def connect_to_voice(ctx):
    if not ctx.voice_client:
        if ctx.author.voice:
            try:
                await ctx.author.voice.channel.connect(timeout=10)
                return True
            except asyncio.TimeoutError:
                await ctx.send("⚠️ Couldn't connect to the voice channel in time.")
            except discord.ClientException:
                await ctx.send("❌ Already connected or unable to connect.")
        else:
            await ctx.send("❌ Join a voice channel to summon the tunes!")
    return False

@bot.command(aliases=["lost", "helfen"])
async def help(ctx):
    """Displays all main commands with dropdown selection, now seasonally flavored."""
    
    form_data = get_seasonal_form_data()

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
                color=form_data["color"],
                title=form_data.get("help_intro", "✨ Echosol Help – Glowing Commands Guide")
            )
            embed.set_footer(text=form_data.get("help_footer", "🌻 Echosol Guide"))

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
                    "📑 **!listtags** – See the beautiful constellation of tags you've created.\n"
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
        title=form_data.get("help_intro", "✨ Welcome to Echosol, your heart's musical companion 💖"),
        description="Let the rhythm guide your soul and the light lead your playlist 🌈🎵",
        color=form_data["color"]
    )
    intro_embed.set_footer(text=form_data.get("help_footer", "🌻 Echosol Guide"))

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

    # Pull seasonal flavor 🍃
    form_data = get_seasonal_form_data()

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
                f"{form_data.get('upload_message', '🌟 Thanks for sharing your musical light! 🌈')}\n"
                f"🎵 Uploaded: **{', '.join(new_files)}**\n"
                f"💫 {form_data.get('tag_prompt', 'Please reply with tags (e.g. `chill`, `sunset`, `epic`) — spaces or commas are fine!')}"
            )
            save_upload_data()
        return

    # Handle tag replies with gentle guidance 💖
    if message.reference and user_id in pending_tag_uploads[guild_id]:
        try:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

        if replied_message.author.id != bot.user.id or not replied_message.content.startswith(form_data.get('upload_message', "🌟 Thank you for sharing your musical light!")):
            return

        tags = [t.strip().lower() for t in message.content.replace(",", " ").split()]
        if not tags:
            await message.channel.send(form_data.get('tag_none_found', "⚠️ Oops! No tags found. Try again with some beautiful labels 🌻"))
            return

        for filename in pending_tag_uploads[guild_id][user_id]:
            if filename not in file_tags_by_guild[guild_id]:
                file_tags_by_guild[guild_id][filename] = []
            file_tags_by_guild[guild_id][filename].extend(tags)

        await message.channel.send(
            f"{form_data.get('tag_success_reply', '🏷️ Your sound sparkles have been tagged! ✨')}\n"
            f"💖 Tagged **{len(pending_tag_uploads[guild_id][user_id])}** file(s) with: `{', '.join(tags)}`"
        )

        del pending_tag_uploads[guild_id][user_id]
        save_upload_data()


# 🌸 Seasonal Flavor Helper 🌞🍂❄️
from datetime import datetime

SEASONAL_FORMS = {
    "vernalight": {
        "name": "🌸 Vernalight Blossoms",
        "color": 0xB3C7F9,
        "bar_emojis": ['🌧️', '☔', '💧', '💮'],
        "unfilled": '🌫️',
        "start_desc": "The soft rain begins to fall — **{song}** flows gently through the mist.",
        "finale_title": "🌸 Petals Fade",
        "finale_desc": "**{song}** dissolves into the morning fog as spring hushes once more.",
        "finale_bar": "🌧️",

        # Play related
        "join_message": "🌧️ The spring rain gently carries Echosol into the voice channel.",
        "leave_message": "🌦️ Echosol drifts quietly from the channel as the petals settle.",
        "no_url_message": "🌱 A song link is needed to plant the next bloom.",
        "connected_message": "🌸 Echosol is now present beneath the spring rain.",
        "playlist_add_message": "🌼 {count} blossoms from the playlist have joined the garden.",
        "single_add_message": "🌷 **{title}** has been planted into the springtime soundscape.",

        # Playback controls
        "pause_message": "🌿 The rain slows as the music pauses for a breath.",
        "resume_message": "🌦️ The rainfall resumes and the melody flows once more.",
        "skip_message": "⏭️ A breeze lifts the melody to its next bloom.",
        "shuffle_message": "🌻 The spring winds have stirred the blossoms into new patterns.",
        "shuffle_too_short_message": "🌱 Not enough blossoms to shuffle — plant more to begin.",

        # Queue displays
        "queue_empty_message": "🌫️ The garden lies quiet... plant new melodies with `!play` or `!listsongs`.",
        "queue_embed_title": "🌸 Vernalight — Blooming Queue",
        "queue_page_empty_message": "🌧️ This page waits quietly for new blooms.",
        "queue_shuffle_success_message": "🌷 The garden has been gently reshuffled by the breeze.",

        # Volume
        "volume_message": "🔊 Volume set to **{volume}%** — soft as rain upon petals.",
        "volume_invalid_message": "🚫 Volume must be between **1 and 100** — even spring has its limits.",

        # Upload system
        "uploads_empty_message": "🌱 No blossoms have been planted yet. Upload a song to begin.",
        "uploads_embed_title": "🌼 Blooming Uploads",
        "uploads_page_empty_message": "🌫️ This page awaits its first spring bloom.",
        "uploads_page_play_message": "🌷 {count} blooms have joined the queue from this page.",
        "uploads_page_shuffle_message": "🌻 The blossoms have been reshuffled into fresh patterns.",
        "uploads_full_shuffle_message": "🌈 All {count} uploaded blossoms are now queued for spring’s concert.",
        "uploads_connect_message": "🌸 Echosol has arrived to tend the spring garden.",
        "uploads_connect_error_message": "❌ A voice channel is needed for the spring melody to begin.",

        # Tag system
        "tag_usage_message": "🌸 Use `!tag <numbers> <tags>` to label blossoms. Example: `!tag 1 2 cozy rain`",
        "tag_valueerror_message": "⚠️ Some song numbers could not be read — check your blossoms again.",
        "tag_missing_args_message": "🌱 Provide both song numbers and tags to nurture your garden.",
        "tag_invalid_number_message": "🌾 Skipped song number {num} — not found in the garden.",
        "tag_success_message": "🏷️ Blossoms tagged: {files} with `{tags}`.",
        "tag_no_tagged_message": "☁️ No blossoms were tagged this time — try again with valid choices.",

        "playbytag_no_args_message": "🌿 Provide at least one tag to gather your blossoms. Example: `!playbytag cozy`",
        "playbytag_no_matches_message": "🌫️ No blossoms found matching tags: `{tags}`.",
        "playbytag_success_message": "🌷 Added {count} blooming tracks tagged `{tags}`.",

        "listtags_empty_message": "🌫️ No tags have been planted yet in this garden.",
        "listtags_title": "🌼 Tags Blooming in the Spring Garden",

        "removetag_missing_args_message": "🌱 Provide song numbers or tags to remove blossoms.",
        "removetag_loading_message": "✨ Pruning the garden... please wait...",
        "removetag_success_message": "🌷 Tags removed from: {files}.",
        "removetag_none_found_message": "🌫️ No tags found to remove from these blossoms.",
        "removetag_invalid_input_message": "⚠️ Some inputs could not be processed: {invalid}",
        "removetag_tag_removed_message": "🏷️ Removed `{tag}` from: {files}.",
        "removetag_tag_not_found_message": "🌫️ No songs carried the tag `{tag}`.",

        # Stop/Clear system
        "stop_active_message": "🌸 Playback has stopped — the rain grows still.",
        "stop_idle_message": "🌷 The spring air is already calm — the queue was clear.",
        "deleteupload_no_args_message": "🌱 Provide upload numbers to remove. Ex: `!du 1 2 3`",
        "deleteupload_success_message": "💫 Released {count} blossoms into the breeze: `{files}`",
        "deleteupload_invalid_numbers_message": "⚠️ Invalid blossoms skipped: `{invalid}`",
        "clearqueue_message": "🌸 The queue has been cleared — fresh blossoms may now grow.",
        "clearuploads_nothing_message": "🌫️ No uploads present — the garden is already empty.",
        "clearuploads_confirm_message": "⚠️ Do you wish to clear **all uploaded blossoms**? This cannot be undone.",
        "clearuploads_success_message": "🌷 {count} blossoms have been cleared from the garden.",
        "clearuploads_cancel_message": "🌱 The spring garden remains undisturbed.",
        "clearuploads_unauthorized_cancel_message": "❌ Only the gardener who summoned this may cancel.",
        "clearuploads_unauthorized_confirm_message": "❌ Only the original gardener may clear the blossoms.",

        "upload_message": "🌧️ Thank you for planting new melodies into the spring garden! 🌼",
        "tag_prompt": "🌱 Reply with tags to help these blossoms bloom. (e.g. `chill`, `rainy morning`, `soft`)",
        "tag_success_reply": "🏷️ Your blossoms have been tagged and are growing beautifully! 🌿",
        "tag_none_found": "☁️ No tags were detected — let’s try planting again!",
        "help_intro": "🌸 Vernalight — Spring whispers, blooming melodies, and soft rain to carry your playlist.",
        "help_footer": "🌿 The garden of songs awaits your touch."
    },

    "solshine": {
        "name": "🌞 Solshine Radiance",
        "color": 0xFFD966,
        "bar_emojis": ['☀️', '🌻', '🌼', '✨'],
        "unfilled": '🌞',
        "start_desc": "**{song}** rises, glowing warm — and a little irresistible — beneath wide open skies.",
        "finale_title": "🌞 Sunset Glow",
        "finale_desc": "**{song}** finishes with a wink as golden light melts into the horizon.",
        "finale_bar": "☀️",

        # Play related
        "join_message": "☀️ Echosol steps into the sunshine — looking good, feeling better.",
        "leave_message": "🌇 The sun dips low, and Echosol takes his leave... but not for long.",
        "no_url_message": "🌞 You bring the song, I bring the glow. Drop that link, gorgeous.",
        "connected_message": "🌻 Echosol settles in — shirtless, obviously — ready to light up your playlist.",
        "playlist_add_message": "🌼 {count} spicy new tracks are now basking in the queue.",
        "single_add_message": "🌷 **{title}** just turned up the summer heat.",

        # Playback controls
        "pause_message": "🌅 The sun lounges for a moment — a little break never hurt anybody.",
        "resume_message": "☀️ Back in the groove — didn’t keep you waiting too long, did I? 😉",
        "skip_message": "⏭️ Next up — I hope you're ready for more heat.",
        "shuffle_message": "🌻 The playlist flirts with a breeze — variety is the spice of summer.",
        "shuffle_too_short_message": "🌱 Not enough songs to stir up — let’s plant a few more, sweetheart.",

        # Queue displays
        "queue_empty_message": "🌞 The stage is empty — time to throw in something worth dancing to.",
        "queue_embed_title": "🌞 Solshine — Heatwave Queue",
        "queue_page_empty_message": "🌻 This part of the playlist could use a little more sunshine.",
        "queue_shuffle_success_message": "🌷 The summer breeze spun the playlist — let’s see where it takes us.",

        # Volume
        "volume_message": "🔊 Volume set to **{volume}%** — hot enough to make hearts race.",
        "volume_invalid_message": "🚫 Let’s not burn up — keep it between 1 and 100, darling.",

        # Upload system
        "uploads_empty_message": "🌞 The sky’s empty — upload a song to start heating things up.",
        "uploads_embed_title": "🌼 Summer Uploads",
        "uploads_page_empty_message": "🌻 This page needs a few more rays of sunshine.",
        "uploads_page_play_message": "🌷 {count} glowing tracks have joined your summer mix.",
        "uploads_page_shuffle_message": "🌻 The uploads just got a playful reshuffle.",
        "uploads_full_shuffle_message": "🌞 All {count} uploaded tracks are ready to sizzle in your queue.",
        "uploads_connect_message": "🌞 Echosol arrives with just the right amount of glow.",
        "uploads_connect_error_message": "❌ You’ve gotta invite me to a voice channel first, sweetheart.",

        # Tag system
        "tag_usage_message": "🌼 Tag those tracks, babe — use `!tag <numbers> <tags>`. Example: `!tag 1 2 summer chill`",
        "tag_valueerror_message": "⚠️ A few of those numbers didn’t land — take another peek.",
        "tag_missing_args_message": "🌱 Gotta give me both the songs and the tags if we're gonna make magic.",
        "tag_invalid_number_message": "🌻 Skipped song number {num} — couldn’t find that one, sunshine.",
        "tag_success_message": "🏷️ Tagged: {files} with `{tags}` — looking good!",
        "tag_no_tagged_message": "☀️ Nothing got tagged this round — wanna try again, cutie?",

        "playbytag_no_args_message": "🌿 Drop a tag to fetch your summer vibes. Example: `!playbytag beach`",
        "playbytag_no_matches_message": "🌞 No songs matched `{tags}` — but we can fix that together.",
        "playbytag_success_message": "🌻 Added {count} hot tracks matching `{tags}`.",

        "listtags_empty_message": "🌞 No tags in bloom yet — let's get you started.",
        "listtags_title": "🌻 Solshine Tags — Sun-Kissed & Sorted",

        "removetag_missing_args_message": "🌱 You gotta tell me what we’re clearing, love.",
        "removetag_loading_message": "✨ Pruning the list... give me just a sec.",
        "removetag_success_message": "🌻 Tags cleared from: {files}.",
        "removetag_none_found_message": "🌞 No tags here to clear — clean as summer skies.",
        "removetag_invalid_input_message": "⚠️ A few inputs tripped me up: {invalid}",
        "removetag_tag_removed_message": "🏷️ Removed `{tag}` from: {files}.",
        "removetag_tag_not_found_message": "🌞 No songs had the tag `{tag}` — easy fix though!",

        # Stop/Clear system
        "stop_active_message": "☀️ The playlist's taking a break — but don’t keep me waiting too long.",
        "stop_idle_message": "🌻 Already quiet here — I was just admiring the view.",
        "deleteupload_no_args_message": "🌱 Drop some file numbers, sugar. Example: `!du 1 2 3`",
        "deleteupload_success_message": "💫 Released {count} tracks into the breeze: `{files}`",
        "deleteupload_invalid_numbers_message": "⚠️ Couldn’t recognize these: `{invalid}`",
        "clearqueue_message": "☀️ Queue cleared — wide open for new heat.",
        "clearuploads_nothing_message": "🌞 Nothing here to clear — just pure sunshine.",
        "clearuploads_confirm_message": "⚠️ You sure you wanna clear **all uploaded songs**? This is permanent, gorgeous.",
        "clearuploads_success_message": "🌻 Cleared {count} uploads — skies wide open now.",
        "clearuploads_cancel_message": "🌞 Left everything untouched — couldn’t say no to you.",
        "clearuploads_unauthorized_cancel_message": "❌ Only the original charmer can cancel this.",
        "clearuploads_unauthorized_confirm_message": "❌ Only the one who started this can clear it out.",

        "upload_message": "☀️ Thanks for dropping some sunshine into the playlist, gorgeous. 🌻",
        "tag_prompt": "🌞 Drop some tags to spice things up. (e.g. `summer vibes`, `heatwave`, `poolside`)",
        "tag_success_reply": "🏷️ Tagged and glowing, babe — looking fine. 🌞",
        "tag_none_found": "🌻 No tags caught the heat. Wanna give it another go?",
        "help_intro": "🌞 Solshine — Turn up the heat, turn up the flirt, and let summer blast through your speakers.",
        "help_footer": "🌻 Summer never ends when you control the playlist."
    },

    "fallchord": {
        "name": "🍂 Fallchord Resonance",
        "color": 0xFF9933,
        "bar_emojis": ['🍁', '🍂', '🦇', '🎃'],
        "unfilled": '🌰',
        "start_desc": "**{song}** drifts in like falling leaves on an autumn breeze.",
        "finale_title": "🍂 Autumn Fade",
        "finale_desc": "**{song}** slips quietly into the dusk, leaving only swirling leaves behind.",
        "finale_bar": "🍁",

        # Play related
        "join_message": "🍂 Echosol drifts in on the breeze — cozy, but watch for shadows.",
        "leave_message": "🌙 The winds shift, and Echosol vanishes like a whispered ghost story.",
        "no_url_message": "🍁 Whisper me your song — let's fill the clearing with sound.",
        "connected_message": "🦇 Echosol perches beneath the trees, ready to spin your autumn melody.",
        "playlist_add_message": "🎃 {count} tunes flutter into the harvest playlist.",
        "single_add_message": "🍎 **{title}** joins the dance beneath the amber moon.",

        # Playback controls
        "pause_message": "🍷 The candles flicker — the melody pauses to sip the evening air.",
        "resume_message": "🍁 The wind stirs again — time to keep dancing through the leaves.",
        "skip_message": "⏭️ A new song rises like mist — onward through the woods.",
        "shuffle_message": "🍂 The forest stirs — your playlist just got shuffled by a playful gust.",
        "shuffle_too_short_message": "🌰 Not quite enough leaves to swirl — add more to the pile.",

        # Queue displays
        "queue_empty_message": "🍂 The clearing is quiet — toss in some tunes and let them fall.",
        "queue_embed_title": "🍁 Fallchord Queue — Dusklit Melodies",
        "queue_page_empty_message": "🎃 This patch waits for melodies to tumble in.",
        "queue_shuffle_success_message": "🍂 The leaves swirl — your queue has been mixed anew.",

        # Volume
        "volume_message": "🔊 Volume set to **{volume}%** — loud enough to echo through the trees.",
        "volume_invalid_message": "🚫 Easy now — don’t wake the spirits. Keep it between 1 and 100.",

        # Upload system
        "uploads_empty_message": "🍂 The woods are still — upload something to break the hush.",
        "uploads_embed_title": "🦇 Autumn Uploads",
        "uploads_page_empty_message": "🍎 This patch of forest is waiting for new songs.",
        "uploads_page_play_message": "🎃 {count} autumn tunes rise like fog into the queue.",
        "uploads_page_shuffle_message": "🍂 The wind plays with your uploads — reshuffled.",
        "uploads_full_shuffle_message": "🍁 All {count} songs swirl together beneath falling leaves.",
        "uploads_connect_message": "🌕 Echosol appears beneath lantern light, ready to begin.",
        "uploads_connect_error_message": "❌ The ritual isn’t complete — hop in a voice channel first.",

        # Tag system
        "tag_usage_message": "🍁 Tag your tunes like fallen leaves: `!tag <numbers> <tags>`. Ex: `!tag 1 2 cozy dusk`",
        "tag_valueerror_message": "⚠️ Some of those song numbers got lost in the fog.",
        "tag_missing_args_message": "🍂 You'll need both numbers and tags for this spell to work.",
        "tag_invalid_number_message": "🌰 Skipped song {num} — couldn't find that leaf.",
        "tag_success_message": "🏷️ The leaves carry your tags: {files} now sparkle with `{tags}`.",
        "tag_no_tagged_message": "🍁 No tags stuck this time — try again beneath the moon.",

        "playbytag_no_args_message": "🌙 Call out a tag to summon the matching tunes. Ex: `!playbytag spooky`",
        "playbytag_no_matches_message": "🍂 No songs matched `{tags}` — perhaps hidden by mist.",
        "playbytag_success_message": "🦇 Summoned {count} tracks under `{tags}`.",

        "listtags_empty_message": "🍁 No tags gathered yet — the forest is quiet.",
        "listtags_title": "🍂 Fallchord Tags — Whispered Among The Trees",

        "removetag_missing_args_message": "🌰 You’ll need to tell me which tags or songs to release.",
        "removetag_loading_message": "✨ Shaking loose the branches... almost there...",
        "removetag_success_message": "🍂 Cleared tags from: {files}.",
        "removetag_none_found_message": "🍎 No tags here to clear — tidy as the autumn sky.",
        "removetag_invalid_input_message": "⚠️ Some slipped between branches: {invalid}",
        "removetag_tag_removed_message": "🏷️ Removed `{tag}` from: {files}.",
        "removetag_tag_not_found_message": "🍂 No songs held the tag `{tag}`.",

        # Stop/Clear system
        "stop_active_message": "🌙 The grove falls still — the melody rests.",
        "stop_idle_message": "🍁 Already silent under moonlit trees.",
        "deleteupload_no_args_message": "🍂 Share some numbers, friend. Ex: `!du 1 2 3`",
        "deleteupload_success_message": "💫 Released {count} songs into the wind: `{files}`",
        "deleteupload_invalid_numbers_message": "⚠️ These slipped through the cracks: `{invalid}`",
        "clearqueue_message": "🍂 Queue cleared — fresh winds await.",
        "clearuploads_nothing_message": "🍁 The forest floor is already clear.",
        "clearuploads_confirm_message": "⚠️ Clear **all uploaded songs**? The woods will stand empty.",
        "clearuploads_success_message": "🍎 Cleared {count} uploads — scattered to the breeze.",
        "clearuploads_cancel_message": "🍂 The songs remain, tucked beneath autumn’s watch.",
        "clearuploads_unauthorized_cancel_message": "❌ Only the one who called may change the winds.",
        "clearuploads_unauthorized_confirm_message": "❌ Only the summoner may clear the grove.",

        "upload_message": "🍁 Your song drifts in like falling leaves — welcome to autumn’s cozy tunes. 🍂",
        "tag_prompt": "🍎 Whisper your tags into the wind. (e.g. `spooky`, `cozy`, `fireside`)",
        "tag_success_reply": "🏷️ Your leaves have been tagged and scattered beneath the trees. 🍃",
        "tag_none_found": "🌫️ No tags rustled — the wind carried them away. Try again?",
        "help_intro": "🍂 Fallchord — Dusky nights, cozy fires, and just a hint of autumn magic in every beat.",
        "help_footer": "🍁 The forest waits, quiet and colorful."
    },

    "frostveil": {
        "name": "❄️ Frostveil Stillness",
        "color": 0x99CCFF,
        "bar_emojis": ['❄️', '💙', '🌨️', '🧊'],
        "unfilled": '🥶',
        "start_desc": "**{song}** begins to swirl softly, like snow through winter air.",
        "finale_title": "❄️ Whispered Silence",
        "finale_desc": "**{song}** drifts into stillness, blanketed beneath crystal frost.",
        "finale_bar": "❄️",

        # Play related
        "join_message": "❄️ Echosol steps in from the snow — safe, warm, and ready to play your tunes.",
        "leave_message": "🌨️ The blizzard carries Echosol softly back into the swirling night.",
        "no_url_message": "☕ Hand me your song — we’ll let it dance like snowflakes.",
        "connected_message": "🧣 Echosol settles in by the hearth, melodies at the ready.",
        "playlist_add_message": "🧤 {count} songs tucked warmly into the queue.",
        "single_add_message": "❄️ **{title}** joins the cozy gathering inside.",

        # Playback controls
        "pause_message": "🥶 The music takes a breath, snowflakes frozen mid-air.",
        "resume_message": "☕ The melody stirs again, warm as cocoa in cold hands.",
        "skip_message": "⏭️ The storm shifts — a new song floats in on the breeze.",
        "shuffle_message": "🌬️ The winds playfully reshuffle your cozy playlist.",
        "shuffle_too_short_message": "🧊 There’s barely enough snow to swirl — add more songs!",

        # Queue displays
        "queue_empty_message": "🌨️ The fireplace crackles — but the song list is empty.",
        "queue_embed_title": "❄️ Frostveil Queue — Hearthside Melodies",
        "queue_page_empty_message": "🥶 This spot is chilly — bring more songs inside.",
        "queue_shuffle_success_message": "🌬️ The storm mixed your queue with a playful gust.",

        # Volume
        "volume_message": "🔊 Volume set to **{volume}%** — enough to echo through frosted windows.",
        "volume_invalid_message": "🚫 Easy — too loud might wake the wind spirits. (1-100)",

        # Upload system
        "uploads_empty_message": "🌨️ The shelves are empty — upload songs to fill the cabin.",
        "uploads_embed_title": "🧊 Frostveil Uploads",
        "uploads_page_empty_message": "❄️ This part of the shelf waits for new songs.",
        "uploads_page_play_message": "☕ {count} cozy tunes now warming the queue.",
        "uploads_page_shuffle_message": "🌬️ The snow stirs — your uploads have been shuffled.",
        "uploads_full_shuffle_message": "🧤 All {count} songs are swirling through the winter wind.",
        "uploads_connect_message": "🕯️ Echosol curls up beside the lights — ready to play.",
        "uploads_connect_error_message": "❌ The fire’s not lit — join a voice channel first.",

        # Tag system
        "tag_usage_message": "❄️ Label your songs like ornaments: `!tag <numbers> <tags>`",
        "tag_valueerror_message": "⚠️ Some of those numbers slipped under the snow.",
        "tag_missing_args_message": "🌬️ Both numbers and tags, please — let's decorate the list.",
        "tag_invalid_number_message": "🧊 Skipped song {num} — couldn’t find it under the snowdrift.",
        "tag_success_message": "🏷️ Songs tagged: {files} with `{tags}` — sparkling like ice crystals.",
        "tag_no_tagged_message": "❄️ No tags stuck this time — let’s try again by the fire.",

        "playbytag_no_args_message": "🧣 Share a tag and we’ll find matching winter tunes.",
        "playbytag_no_matches_message": "🌬️ No songs matched `{tags}` — lost somewhere in the snow.",
        "playbytag_success_message": "🌨️ Brought {count} songs into the warm under `{tags}`.",

        "listtags_empty_message": "❄️ No tags yet — the shelves are bare.",
        "listtags_title": "🌨️ Frostveil Tags — Tucked Beneath The Snow",

        "removetag_missing_args_message": "🧊 Tell me which tags or songs to gently unhook.",
        "removetag_loading_message": "✨ Sweeping snow off the shelves... hold tight...",
        "removetag_success_message": "❄️ Tags cleared from: {files}.",
        "removetag_none_found_message": "🥶 No tags found to clear — all tidy and still.",
        "removetag_invalid_input_message": "⚠️ A few slipped through the cracks: {invalid}",
        "removetag_tag_removed_message": "🏷️ Removed `{tag}` from: {files}.",
        "removetag_tag_not_found_message": "🌨️ No songs carried the tag `{tag}`.",

        # Stop/Clear system
        "stop_active_message": "🌬️ The cabin grows quiet — the storm whispers outside.",
        "stop_idle_message": "❄️ Already silent, with snow softly falling.",
        "deleteupload_no_args_message": "☕ Share some song numbers to clear. Ex: `!du 1 2 3`",
        "deleteupload_success_message": "💫 Released {count} songs back into the snowy night: `{files}`",
        "deleteupload_invalid_numbers_message": "⚠️ Couldn’t find these under the snow: `{invalid}`",
        "clearqueue_message": "🌨️ The queue is cleared — time for fresh snow to fall.",
        "clearuploads_nothing_message": "🧤 Nothing here — the shelves are already empty.",
        "clearuploads_confirm_message": "⚠️ Clear **all uploaded songs**? The cabin shelves will be empty.",
        "clearuploads_success_message": "☕ Cleared {count} uploads — ready for new cozy songs.",
        "clearuploads_cancel_message": "❄️ The songs remain safe inside for another night.",
        "clearuploads_unauthorized_cancel_message": "❌ Only the one who lit the fire may change this.",
        "clearuploads_unauthorized_confirm_message": "❌ Only the summoner may clear the shelves.",

        "upload_message": "❄️ Your song drifts softly inside, away from the swirling snow. 🧤",
        "tag_prompt": "☕ Wrap your tags up nice and warm. (e.g. `snowfall`, `fireplace`, `holiday`)",
        "tag_success_reply": "🏷️ Tagged and tucked in safe like snowflakes under a blanket. 🧣",
        "tag_none_found": "🌨️ No tags caught in the snow. Let’s try again with gloves this time!",
        "help_intro": "❄️ Frostveil — Warm cocoa, soft lights, and melodies swirling like snow outside the window.",
        "help_footer": "🧣 Stay warm, stay cozy — and let the music glow."

    },

    "default": {

        "name": "🎵 Echosol Harmonies",
        "color": 0xFFDB8A,
        "bar_emojis": ['🎵', '🎶', '🎼', '🎧'],
        "unfilled": '🔅',
        "start_desc": "🎶 **{song}** takes the stage — lean back, I've got your vibe covered.",
        "finale_title": "🎵 The Fadeout",
        "finale_desc": "**{song}** drifts off like a satisfied sigh.",
        "finale_bar": "✨",

        "join_message": "🎧 Sliding in — lights warm, sound smooth, vibe ready.",
        "leave_message": "🌙 Fading out — but you know where to find me when you need the music.",
        "no_url_message": "🎶 Don't be shy — drop me a track, let's make magic.",
        "connected_message": "🎛️ All set — let’s turn this quiet room into a concert.",
        "playlist_add_message": "🎼 {count} new tracks locked in. The night’s looking good.",
        "single_add_message": "🎵 **{title}** queued — can't wait to hear how it shines.",

        "pause_message": "⏸️ Holding the beat — anticipation can be sweet.",
        "resume_message": "▶️ Right where we left off — let it flow.",
        "skip_message": "⏭️ Skipping ahead — next song, show us what you’ve got.",
        "shuffle_message": "🔀 Stirring the pot — let’s see what magic comes up.",
        "shuffle_too_short_message": "🎧 A little thin for shuffling — add a few more gems first.",

        "queue_empty_message": "🎵 The stage is clear. Your move, maestro.",
        "queue_embed_title": "🎶 Echosol Queue — The Setlist",
        "queue_page_empty_message": "🎧 No songs here... let’s fix that, yeah?",
        "queue_shuffle_success_message": "🔀 Shuffled — mystery is half the fun.",

        "volume_message": "🔊 Volume set to **{volume}%** — perfect balance, like a fine cocktail.",
        "volume_invalid_message": "🚫 Easy now. 1 to 100 only — we want hearts fluttering, not eardrums popping.",

        "uploads_empty_message": "🎶 No uploads yet — bring me your favorite tracks, let’s build a vibe.",
        "uploads_embed_title": "🎼 Uploaded Library",
        "uploads_page_empty_message": "🎧 No uploads on this page — room to grow.",
        "uploads_page_play_message": "🎵 {count} tracks pulled — let’s spin them up.",
        "uploads_page_shuffle_message": "🔀 Uploads shuffled — mystery mix incoming.",
        "uploads_full_shuffle_message": "🎶 All {count} uploads spinning in — full house tonight.",
        "uploads_connect_message": "🎙️ Connected and standing by — you run the playlist, I run the room.",
        "uploads_connect_error_message": "❌ Hop in a voice channel — then let me do my thing.",

        "tag_usage_message": "🏷️ Tag your tracks: `!tag <numbers> <tags>` (e.g. `!tag 1 chill vibe`)",
        "tag_valueerror_message": "⚠️ Some of those numbers didn’t vibe — check your list.",
        "tag_missing_args_message": "🎶 I need both song numbers and those sweet tags.",
        "tag_invalid_number_message": "🎼 Skipped song {num} — couldn’t locate it.",
        "tag_success_message": "🏷️ Tagged {files} with `{tags}` — your vibe catalog grows.",
        "tag_no_tagged_message": "🎶 No tags applied — another round?",

        "playbytag_no_args_message": "🎧 Toss me a tag — I’ll find matching vibes.",
        "playbytag_no_matches_message": "🎵 No matches for `{tags}` — want to tag some more gems?",
        "playbytag_success_message": "🎶 Found {count} under `{tags}` — ready to roll.",

        "listtags_empty_message": "🏷️ No tags yet — clean slate, full of possibilities.",
        "listtags_title": "🎼 Your Song Tags",

        "removetag_missing_args_message": "🎧 You gotta tell me which tags or songs to clear.",
        "removetag_loading_message": "✨ Untangling tags... almost done...",
        "removetag_success_message": "🏷️ Tags cleared from: {files}.",
        "removetag_none_found_message": "🎧 Nothing found to clear — looking tidy already.",
        "removetag_invalid_input_message": "⚠️ Some inputs didn’t land: {invalid}",
        "removetag_tag_removed_message": "🏷️ Tag `{tag}` removed from: {files}.",
        "removetag_tag_not_found_message": "🎵 No tracks carried `{tag}`.",

        "stop_active_message": "🎧 Playback paused, queue cleared — standing by.",
        "stop_idle_message": "🎵 Already quiet — ready whenever you are.",
        "deleteupload_no_args_message": "🎧 Drop song numbers to clear — ex: `!du 1 2 3`",
        "deleteupload_success_message": "💫 Deleted {count} uploads: `{files}`",
        "deleteupload_invalid_numbers_message": "⚠️ These didn’t register: `{invalid}`",
        "clearqueue_message": "🎼 Queue cleared — next vibe incoming.",
        "clearuploads_nothing_message": "🎧 Nothing to clear — you’re starting fresh.",
        "clearuploads_confirm_message": "⚠️ You sure you want to wipe **all uploads**? This is permanent.",
        "clearuploads_success_message": "🎼 Cleared {count} uploads — clean slate.",
        "clearuploads_cancel_message": "🎧 No worries — your uploads are untouched.",
        "clearuploads_unauthorized_cancel_message": "❌ Only the person who requested can cancel.",
        "clearuploads_unauthorized_confirm_message": "❌ Only the original requestor may clear uploads.",

        "upload_message": "🎶 New track received — added straight to the vibe locker. 🎧",
        "tag_prompt": "🏷️ Toss me your tags, let’s get these categorized. (e.g. `lofi`, `hype`, `roadtrip`)",
        "tag_success_reply": "🏷️ Tagged and filed — your playlist just leveled up. 🎼",
        "tag_none_found": "🎧 No tags caught — try again to flavor it up.",
        "help_intro": "🎵 Echosol Harmonies — smooth vibes, perfect balance, ready for any tune you bring.",
        "help_footer": "🎧 The stage is yours — let the music flow."

    }
}
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

def get_seasonal_form_data():
    form = get_current_form()
    return SEASONAL_FORMS.get(form, SEASONAL_FORMS["default"])

@bot.command(aliases=["playwithme", "connect", "verbinden", "kisses"])
async def join(ctx):
    """Joins a voice channel, seasonally flavored."""
    form_data = get_seasonal_form_data()

    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(form_data.get("join_message", "💫 Echosol has joined you in song and spirit!"))
    else:
        await ctx.send("❌ Echosol cannot find your spirit... Join a voice channel first!")

@bot.command(aliases=["goaway", "disconnect", "verlassen"])
async def leave(ctx):
    """Leaves the voice channel with seasonal sparkle."""
    form_data = get_seasonal_form_data()

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send(form_data.get("leave_message", "🌅 Echosol has gently drifted from the voice channel, returning to the cosmos. 💫"))
    else:
        await ctx.send("🌙 I'm not shining in any voice channel right now.")

@bot.command(aliases=["p", "gimme", "spielen"])
async def play(ctx, url: str = None):
    """Plays a song from YouTube or adds it to the queue with seasonal flavor."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()

    if not url:
        await ctx.send(form_data["no_url_message"])
        return

    connected = await connect_to_voice(ctx)
    if not connected:
        return
    else:
        await ctx.send(form_data["connected_message"])

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
                await ctx.send(form_data["playlist_add_message"].format(count=added))
            else:  # Single video
                song_queue_by_guild[guild_id].append((info['webpage_url'], info['title']))
                await ctx.send(form_data["single_add_message"].format(title=info['title']))

    except Exception as e:
        await ctx.send(f"⚠️ A cloud blocked the song: `{e}`")
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client
    form_data = get_seasonal_form_data()

    if vc and vc.is_playing():
        return

    if not song_queue_by_guild[guild_id]:
        await ctx.send(form_data.get("queue_empty_message", "🌈 The stage awaits new tunes!"))
        return

    usage_counters[guild_id] += 1
    is_high_usage = usage_counters[guild_id] >= 30

    if last_now_playing_message_by_guild.get(guild_id):
        try:
            embed = last_now_playing_message_by_guild[guild_id].embeds[0]
            embed.set_field_at(0, name="Progress", value="💤 This song has finished playing. `Complete`", inline=False)
            await last_now_playing_message_by_guild[guild_id].edit(embed=embed)
        except Exception:
            pass
        last_now_playing_message_by_guild[guild_id] = None

    song_data = song_queue_by_guild[guild_id].pop(0)
    is_temp_youtube = False

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

    def after_play(error):
        if error:
            print(f"⚠️ Playback error: {error}")
        if is_temp_youtube and os.path.exists(song_url):
            try:
                os.remove(song_url)
            except Exception as e:
                print(f"[Cleanup Error] Could not delete file: {e}")
        asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

    vc.play(discord.FFmpegPCMAudio(song_url, **ffmpeg_options), after=after_play)
    vc.source = discord.PCMVolumeTransformer(vc.source, volume_levels_by_guild[guild_id])

    # Seasonal progress bar (fixed for custom emoji handling)
    def seasonal_progress_bar(current, total, segments=10):
        filled = int((current / total) * segments) if total > 0 else 0
        emojis = form_data["bar_emojis"]
        filled_icon = emojis[0]
        pulse_icon = emojis[1] if len(emojis) > 1 else filled_icon  # fallback if only 1 emoji
        unfilled_icon = form_data.get("unfilled", "▫️")
        return ''.join(
            f"{filled_icon}" if i < filled else f"{pulse_icon}" if i == filled else f"{unfilled_icon}"
            for i in range(segments)
        )

    progress_bar_func = seasonal_progress_bar

    embed = discord.Embed(
        title=form_data["name"],
        description=form_data.get("start_desc", f"🎶 **{song_title}** is playing!").format(song=song_title),
        color=form_data["color"]
    )

    if duration:
        embed.add_field(name="Progress", value=f"{progress_bar_func(0, duration)} `0:00 / {duration // 60}:{duration % 60:02d}`", inline=False)

    message = await ctx.send(embed=embed)
    last_now_playing_message_by_guild[guild_id] = message

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

        try:
            embed.title = form_data.get("finale_title", "🌟 Finale Glow")
            embed.description = form_data.get("finale_desc", "**{song}** just finished playing.").format(song=song_title)
            finale_bar = form_data.get("finale_bar", "✨")
            embed.set_field_at(0, name="Progress", value=f"{finale_bar * 10} `Finished`", inline=False)
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
    """Shuffles the current music queue with seasonal joy."""
    form_data = get_seasonal_form_data()
    guild_id = ctx.guild.id
    queue = song_queue_by_guild.get(guild_id, [])

    if len(queue) > 1:
        random.shuffle(queue)
        await ctx.send(form_data.get("shuffle_message", "🔀 The playlist has been shuffled!"))
    else:
        await ctx.send(form_data.get("shuffle_too_short_message", "🌱 Not enough tunes to shuffle — add more!"))

@bot.command(aliases=["hush"])
async def pause(ctx):
    """Pauses the current song with seasonal hush."""
    form_data = get_seasonal_form_data()

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send(form_data.get("pause_message", "💤 The music takes a gentle pause."))

@bot.command(aliases=["youmayspeak"])
async def resume(ctx):
    """Resumes paused music with seasonal flavor."""
    form_data = get_seasonal_form_data()

    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send(form_data.get("resume_message", "💓 The melody resumes — flowing once more!"))

@bot.command(aliases=["nextplease", "next", "skippy"])
async def skip(ctx):
    """Skips the current song with seasonal flavor."""
    form_data = get_seasonal_form_data()

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await play_next(ctx)
        await ctx.send(form_data.get("skip_message", "⏭ Skipping to the next song!"))

@bot.command(aliases=["turnitup", "tooloud", "v"])
async def volume(ctx, volume: int):
    """Sets the bot's volume with seasonal warmth."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()

    if 1 <= volume <= 100:
        volume_levels_by_guild[guild_id] = volume / 100.0

        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = volume_levels_by_guild[guild_id]

        await ctx.send(form_data.get("volume_message", f"🔊 Volume set to **{volume}%**").format(volume=volume))
    else:
        await ctx.send(form_data.get("volume_invalid_message", "🚫 Volume must be between 1 and 100."))

@bot.command(aliases=["whatsnext", "q"])
async def queue(ctx):
    """Displays the current queue with pagination and a shuffle button."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()

    if not song_queue_by_guild[guild_id]:
        await ctx.send(form_data.get("queue_empty_message", "🌥️ The queue is empty... add more songs!"))
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
                title=form_data.get("queue_embed_title", f"🎶 Echosol Queue — Page {self.page + 1}"),
                description=queue_display or form_data.get("queue_page_empty_message", "🌤️ This page is feeling a little empty..."),
                color=form_data.get("color", 0xFFE680)
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
            await interaction.response.send_message(
                form_data.get("queue_shuffle_success_message", "🔀 Queue reshuffled!"), ephemeral=True
            )
            await self.send_page(interaction)

    view = QueuePages(guild_id)
    await view.send_page(message=await ctx.send(view=view))

@bot.command(aliases=["whatwegot"])
async def listsongs(ctx):
    """Lists available uploaded songs with optional tag filter, pagination, and actions."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()

    if not uploaded_files_by_guild[guild_id]:
        await ctx.send(form_data.get("uploads_empty_message", "🌥️ No uploads yet — upload a song to begin."))
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
        title = form_data.get("uploads_embed_title", "📂 Uploaded Songs")
        if state.selected_tag:
            title += f" – Tag: {state.selected_tag}"

        embed = discord.Embed(
            title=f"{title} (Page {state.current_page + 1}/{total_pages})",
            description=song_list or form_data.get("uploads_page_empty_message", "☁️ No songs here yet."),
            color=form_data.get("color", 0xFFE680)
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

            message_template = form_data.get("uploads_page_play_message", "🎵 Queued {count} songs from this page.")
            await interaction.response.send_message(
                message_template.format(count=len(added)),
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

            message_template = form_data.get("uploads_page_shuffle_message", "🔀 Shuffled {count} songs from this page.")
            await interaction.response.send_message(
                message_template.format(count=len(added)),
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
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])
    song_queue = song_queue_by_guild.setdefault(guild_id, [])

    if not uploaded_files:
        await ctx.send(form_data.get("uploads_empty_message", "🌥️ No songs uploaded yet."))
        return

    shuffled_songs = uploaded_files[:]
    random.shuffle(shuffled_songs)

    for filename in shuffled_songs:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue.append(song_path)

    message_template = form_data.get(
        "uploads_full_shuffle_message",
        "🌈 {count} uploaded songs have been shuffled into your queue."
    )
    await ctx.send(message_template.format(count=len(shuffled_songs)))

    # 🔌 Safer connection logic
    connected = await connect_to_voice(ctx)
    if not connected:
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["pp", "seite", "page", "playpage"])
async def playbypage(ctx, *pages):
    """Plays one or more pages of uploaded songs."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])

    if not uploaded_files:
        await ctx.send(form_data.get("uploads_empty_message", "🌥️ No uploads found yet."))
        return

    per_page = 10
    total_pages = (len(uploaded_files) + per_page - 1) // per_page
    added = []

    if not pages:
        await ctx.send("🌻 Please provide one or more page numbers to load songs. (e.g. `!page 1 2 3`)")
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
        await ctx.send("❌ No songs added. Try again with valid pages.")
        return

    message_template = form_data.get("uploads_page_play_message", "🎶 Added {count} songs from selected pages.")
    await ctx.send(message_template.format(count=len(added)))

    connected = await connect_to_voice(ctx)
    if not connected:
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["number", "playnumber", "n"])
async def playbynumber(ctx, *numbers):
    """Plays one or multiple uploaded songs using their numbers (per-server)."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])
    song_queue = song_queue_by_guild.setdefault(guild_id, [])

    added_songs = []

    if not numbers:
        await ctx.send(form_data.get("uploads_empty_message", "❌ Please provide one or more song numbers."))
        return

    for num in numbers:
        try:
            num = int(num.strip(','))
            if 1 <= num <= len(uploaded_files):
                song_path = os.path.join(MUSIC_FOLDER, uploaded_files[num - 1])
                song_queue.append(song_path)
                added_songs.append(uploaded_files[num - 1])
            else:
                await ctx.send(f"⚠️ Song number `{num}` is out of range. Use `!listsongs` to see available tracks.")
        except ValueError:
            await ctx.send(f"❌ `{num}` isn’t a valid number. Use spaces or commas to separate multiple.")

    if not added_songs:
        await ctx.send("🌧️ No songs were added — try again with valid numbers.")
        return

    success_message = form_data.get("uploads_page_play_message", "🎶 Added {count} songs.")
    await ctx.send(success_message.format(count=len(added_songs)))

    connected = await connect_to_voice(ctx)
    if not connected:
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["flag", "etikett"])
async def tag(ctx, *args):
    """Tags one or more uploaded songs. Usage: !tag <number(s)> <tags...> (per-server)"""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])
    file_tags = file_tags_by_guild.setdefault(guild_id, {})

    if len(args) < 2:
        usage_message = form_data.get(
            "tag_usage_message",
            "🏷️ Use `!tag <numbers> <tags>` to apply tags. Example: `!tag 1 2 chill vibe`"
        )
        await ctx.send(usage_message)
        return

    try:
        numbers = [int(arg) for arg in args if arg.isdigit()]
        tags = [arg.lower() for arg in args if not arg.isdigit()]
    except ValueError:
        valueerror_message = form_data.get(
            "tag_valueerror_message",
            "⚠️ Some song numbers didn’t parse correctly — please use numbers only."
        )
        await ctx.send(valueerror_message)
        return

    if not numbers or not tags:
        missing_args_message = form_data.get(
            "tag_missing_args_message",
            "🏷️ Please provide both song numbers and tags."
        )
        await ctx.send(missing_args_message)
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
            invalid_num_message = form_data.get(
                "tag_invalid_number_message",
                f"⚠️ Skipped song number {num} — not found."
            )
            await ctx.send(invalid_num_message.format(num=num))

    if tagged:
        success_message = form_data.get(
            "tag_success_message",
            "🏷️ Tagged: {files} with `{tags}`"
        )
        await ctx.send(success_message.format(
            files=", ".join(tagged),
            tags=", ".join(tags)
        ))
        save_upload_data()
    else:
        no_tagged_message = form_data.get(
            "tag_no_tagged_message",
            "☁️ No songs were tagged — please try again."
        )
        await ctx.send(no_tagged_message)

@bot.command(aliases=["tagplay", "greenflag", "pt"])
async def playbytag(ctx, *search_tags):
    """Plays all uploaded songs that match one or more tags. Usage: !playbytag chill vibe (per-server)"""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])
    file_tags = file_tags_by_guild.setdefault(guild_id, {})

    if not uploaded_files:
        empty_message = form_data.get(
            "uploads_empty_message",
            "🌥️ No uploads yet — add some sunshine first with an upload."
        )
        await ctx.send(empty_message)
        return

    if not search_tags:
        no_args_message = form_data.get(
            "playbytag_no_args_message",
            "🌿 Please share at least one tag. Example: `!playbytag chill`"
        )
        await ctx.send(no_args_message)
        return

    tags_lower = [t.lower() for t in search_tags]
    matched = [
        f for f in uploaded_files
        if any(tag in file_tags.get(f, []) for tag in tags_lower)
    ]

    if not matched:
        no_matches_message = form_data.get(
            "playbytag_no_matches_message",
            "☁️ No songs found glowing with tag(s): `{tags}`."
        )
        await ctx.send(no_matches_message.format(tags=", ".join(tags_lower)))
        return

    for filename in matched:
        song_path = os.path.join(MUSIC_FOLDER, filename)
        song_queue_by_guild.setdefault(guild_id, []).append(song_path)

    success_message = form_data.get(
        "playbytag_success_message",
        "🌈 Added {count} tracks matching `{tags}` to the queue."
    )
    await ctx.send(success_message.format(count=len(matched), tags=", ".join(tags_lower)))

    connected = await connect_to_voice(ctx)
    if not connected:
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["whiteflag", "viewtags", "showtags"])
async def listtags(ctx):
    """Shows all tags currently in use for uploaded songs (per-server)."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    file_tags = file_tags_by_guild.setdefault(guild_id, {})

    # Gather all unique tags
    unique_tags = set()
    for tags in file_tags.values():
        unique_tags.update(tags)

    if not unique_tags:
        empty_message = form_data.get(
            "listtags_empty_message",
            "🌫️ No tags exist yet — nothing is dancing in the air."
        )
        await ctx.send(empty_message)
        return

    sorted_tags = sorted(unique_tags)
    tag_text = ", ".join(sorted_tags)

    max_length = 4000  # Leave room for formatting and footer
    if len(tag_text) > max_length:
        trimmed = tag_text[:max_length]
        last_comma = trimmed.rfind(",")
        trimmed = trimmed[:last_comma] + "..."
        description = f"`{trimmed}`\n\n⚠️ Some tags are hidden due to space. Use filters to browse!"
    else:
        description = f"`{tag_text}`"

    embed_title = form_data.get(
        "listtags_title",
        "🌼 Tags Blooming in the Archive"
    )

    embed = discord.Embed(
        title=embed_title,
        description=description,
        color=discord.Color.from_str("#ffb6c1")
    )
    embed.set_footer(text="Tag your uploads to help them shine brighter ✨")

    await ctx.send(embed=embed)

@bot.command(aliases=["untag", "deletetag", "cleartags"])
async def removetag(ctx, *args):
    """Removes all tags from specified songs, or removes a specific tag from all songs."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    file_tags = file_tags_by_guild.setdefault(guild_id, {})
    uploaded_files = uploaded_files_by_guild.setdefault(guild_id, [])

    if not args:
        embed = discord.Embed(
            title=form_data.get("removetag_missing_args_message", "🌸 Oops! Missing Details"),
            description="Please use:\n\n"
                        "➔ `!removetag <song number(s)>` to clear all tags from songs.\n"
                        "➔ `!removetag <tag>` to remove a tag from all songs.",
            color=discord.Color.from_str("#ffb6c1")
        )
        await ctx.send(embed=embed)
        return

    loading_message_text = form_data.get("removetag_loading_message", "✨ Working... please wait... 🎵")
    loading_message = await ctx.send(loading_message_text)
    await asyncio.sleep(1)

    did_change = False

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
                    did_change = True

        if cleared:
            cleared_message = form_data.get("removetag_success_message", "Tags cleared from: {files}.")
            embed = discord.Embed(
                title="✅ Tags Cleared",
                description=cleared_message.format(files=", ".join(cleared)),
                color=discord.Color.from_str("#fff0b3")
            )
            embed.set_footer(text="✨ Fresh, tag-free melodies await.")
        else:
            no_tags_message = form_data.get("removetag_none_found_message", "No tags found to clear.")
            embed = discord.Embed(
                title="🌥️ No Tags Found",
                description=no_tags_message,
                color=discord.Color.from_str("#add8e6")
            )

        if invalid:
            invalid_message = form_data.get("removetag_invalid_input_message", "⚠️ Invalid: {invalid}")
            embed.add_field(
                name="⚠️ Ignored Inputs",
                value=invalid_message.format(invalid=", ".join(invalid)),
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
                did_change = True

        if removed_from:
            tag_removed_message = form_data.get("removetag_tag_removed_message", "Removed `{tag}` from: {files}.")
            embed = discord.Embed(
                title="🏷️ Tag Removed",
                description=tag_removed_message.format(tag=tag_to_remove, files=", ".join(removed_from)),
                color=discord.Color.from_str("#ffd1dc")
            )
            embed.set_footer(text="✨ The songs now float free.")
        else:
            not_found_message = form_data.get("removetag_tag_not_found_message", f"No songs carried the tag `{tag_to_remove}`.")
            embed = discord.Embed(
                title="🌫️ No Songs Found",
                description=not_found_message,
                color=discord.Color.from_str("#d3d3f3")
            )

        await loading_message.edit(content=None, embed=embed)

    if did_change:
        save_upload_data()

@bot.command(aliases=["shutup", "nomore", "stoppen"])
async def stop(ctx):
    """Stops playback and clears the queue."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    song_queue_by_guild[guild_id] = []

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send(form_data.get("stop_active_message", "🌤️ Playback has stopped — the melody rests."))
    else:
        await ctx.send(form_data.get("stop_idle_message", "🕊️ Already silent, but your queue has been cleared."))

@bot.command(aliases=["delete", "removeupload", "du", "byebish"])
async def deleteupload(ctx, *numbers):
    """Deletes one or multiple uploaded songs by their numbers (from !listsongs)."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])
    file_tags = file_tags_by_guild.get(guild_id, {})

    if not numbers:
        await ctx.send(form_data.get("deleteupload_no_args_message", "🌱 Please share which songs to release."))
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

    for filename in deleted:
        if filename in uploaded_files:
            uploaded_files.remove(filename)
        if filename in file_tags:
            del file_tags[filename]

    uploaded_files_by_guild[guild_id] = uploaded_files
    file_tags_by_guild[guild_id] = file_tags
    save_upload_data()

    if deleted:
        await ctx.send(
            form_data.get("deleteupload_success_message", "💫 Deleted files: {files}").format(
                count=len(deleted),
                files=", ".join(deleted)
            )
        )
    if invalid:
        await ctx.send(
            form_data.get("deleteupload_invalid_numbers_message", "⚠️ Skipped invalid inputs: {invalid}").format(
                invalid=", ".join(invalid)
            )
        )

@bot.command(aliases=["spankies", "cq"])
async def clearqueue(ctx):
    """Clears the music queue for this server only."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    song_queue_by_guild[guild_id] = []

    await ctx.send(form_data.get("clearqueue_message", "🌈 The queue has been cleared — fresh vibes await."))

@bot.command(aliases=["exterminate", "cu"])
async def clearuploads(ctx):
    """Deletes all uploaded files for this server to free space, with confirmation."""
    guild_id = ctx.guild.id
    form_data = get_seasonal_form_data()
    uploaded_files = uploaded_files_by_guild.get(guild_id, [])

    if not uploaded_files:
        await ctx.send(form_data.get("clearuploads_nothing_message", "🌥️ Nothing to clear — skies are already clear."))
        return

    class ConfirmClearView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=15)

        @discord.ui.button(label="✅ Yes, clear all", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message(
                    form_data.get("clearuploads_unauthorized_confirm_message", "❌ Only the summoner may clear the uploads."),
                    ephemeral=True
                )
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

            save_upload_data()

            await interaction.response.edit_message(
                content=form_data.get(
                    "clearuploads_success_message",
                    f"💫 Released {file_count} files."
                ).format(count=file_count),
                view=None
            )

        @discord.ui.button(label="❌ Cancel", style=discord.ui.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user == ctx.author:
                await interaction.response.edit_message(
                    content=form_data.get("clearuploads_cancel_message", "❄️ Clear cancelled."),
                    view=None
                )
            else:
                await interaction.response.send_message(
                    form_data.get("clearuploads_unauthorized_cancel_message", "❌ Only the original caller can cancel."),
                    ephemeral=True
                )

    await ctx.send(
        form_data.get("clearuploads_confirm_message", "⚠️ Are you sure you want to clear all uploads? This cannot be undone."),
        view=ConfirmClearView()
    )

# ------ Playlist Commands (attach these to your existing bot) ------

@bot.command(aliases=["mkplaylist", "newlist"])
async def createplaylist(ctx, playlist_name: str):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)
    
    if playlist_name in playlists_by_guild[guild_id]:
        await ctx.send(f"🚫 Playlist `{playlist_name}` already exists!")
        return

    playlists_by_guild[guild_id][playlist_name] = []
    save_playlists()
    await ctx.send(f"🎶 Created new playlist: `{playlist_name}`!")

@bot.command(aliases=["rmlist", "deletepl"])
async def deleteplaylist(ctx, playlist_name: str):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)

    if playlist_name not in playlists_by_guild[guild_id]:
        await ctx.send(f"🚫 Playlist `{playlist_name}` doesn’t exist!")
        return

    del playlists_by_guild[guild_id][playlist_name]
    save_playlists()
    await ctx.send(f"🗑️ Deleted playlist `{playlist_name}`.")

@bot.command(aliases=["addsong", "pladd"])
async def addtoplaylist(ctx, playlist_name: str, *, url: str):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)

    if playlist_name not in playlists_by_guild[guild_id]:
        await ctx.send(f"🚫 Playlist `{playlist_name}` not found!")
        return

    playlists_by_guild[guild_id][playlist_name].append(url)
    save_playlists()
    await ctx.send(f"✅ Added to `{playlist_name}`!")

@bot.command(aliases=["addq", "pladdqueue"])
async def addqueue(ctx, playlist_name: str):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)

    if playlist_name not in playlists_by_guild[guild_id]:
        await ctx.send(f"🚫 Playlist `{playlist_name}` not found!")
        return

    queue = song_queue_by_guild.get(ctx.guild.id, [])
    if not queue:
        await ctx.send("🌥️ Nothing in queue to add!")
        return

    for song_path in queue:
        playlists_by_guild[guild_id][playlist_name].append(song_path)
    save_playlists()
    await ctx.send(f"✅ Added {len(queue)} songs to `{playlist_name}`!")

@bot.command(aliases=["remsong", "plremove"])
async def removefromplaylist(ctx, playlist_name: str, index: int):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)

    if playlist_name not in playlists_by_guild[guild_id]:
        await ctx.send(f"🚫 Playlist `{playlist_name}` not found!")
        return

    try:
        removed = playlists_by_guild[guild_id][playlist_name].pop(index - 1)
        save_playlists()
        await ctx.send(f"🗑️ Removed: `{removed}` from `{playlist_name}`.")
    except IndexError:
        await ctx.send(f"🚫 Invalid index — playlist only has {len(playlists_by_guild[guild_id][playlist_name])} items.")

@bot.command(aliases=["myplaylists", "listsaved"])
async def listplaylists(ctx):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)

    playlists = playlists_by_guild[guild_id]
    if not playlists:
        await ctx.send("📂 No playlists yet!")
        return

    embed = discord.Embed(title="🎶 Your Playlists:", color=discord.Color.blurple())
    for name, items in playlists.items():
        embed.add_field(name=name, value=f"{len(items)} song(s)", inline=False)

    await ctx.send(embed=embed)

@bot.command(aliases=["plplay"])
async def playplaylist(ctx, playlist_name: str):
    guild_id = str(ctx.guild.id)
    ensure_guild_playlists(guild_id)
    form_data = get_seasonal_form_data()

    if playlist_name not in playlists_by_guild[guild_id]:
        await ctx.send(f"🚫 Playlist `{playlist_name}` not found!")
        return

    playlist = playlists_by_guild[guild_id][playlist_name]
    if not playlist:
        await ctx.send("🌥️ Playlist is empty!")
        return

    for item in playlist:
        song_queue_by_guild[guild_id].append(item)

    await ctx.send(f"🎧 Queued `{len(playlist)}` songs from `{playlist_name}`!")

    connected = await connect_to_voice(ctx)
    if not connected:
        return

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(aliases=["backupecho"])
async def backupechosol(ctx):
    try:
        with open(PLAYLISTS_FILE, "rb") as f:
            await ctx.send("📂 Playlist backup:", file=discord.File(f, PLAYLISTS_FILE))
    except Exception as e:
        await ctx.send(f"🚫 Backup failed: {e}")

# Run the bot
TOKEN = os.getenv("TOKEN")  # Reads token from environment variables
load_upload_data()
load_playlists()
bot.run(TOKEN)