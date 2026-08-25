import io
import json
import os
import random
import re
import sqlite3
from asyncio import Lock
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get


QUESTION_LOG_FILE = "./databases/questionlog.json"
CONTRIBUTOR_DATABASE_FILE = "./databases/contributors.sqlite3"

CREDIT_ROLE_NAMES = (
    "Teaching Assistant",
    "Top Student",
    "Commissioner",
)

POLL_CHANNEL_IDS = {
    1082467211291148351,
    1092807840256766012,
    1153733706821935125,
}

QUESTION_CHANNEL_NAMES = {
    "superadminchannel",
    "dev-questions",
}

QUESTION_EXEMPT_USERNAMES = {
    "maslina8",
    "mmcc_94868",
}

poll_lock = Lock()
contributor_lock = Lock()

polldata = {}
activepollfile = ""
questionlog = {}

emojipairs = {
    "⚔️": "Rusted Swords",
    "❤️": "The Shapes of Love",
    "👣": "Stride Alone",
    "⭐": "The Price of Fame",
    "🩹": "A Whole Human",
    "⌛": "Memories of A Future",
    "⚖️": "The Laws of Night",
}


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temporary_path = path + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    os.replace(temporary_path, path)


def connect_contributor_database():
    directory = os.path.dirname(CONTRIBUTOR_DATABASE_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)

    connection = sqlite3.connect(CONTRIBUTOR_DATABASE_FILE)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_contributor_database():
    with connect_contributor_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contributors (
                user_id TEXT NOT NULL,
                role_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                username TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                PRIMARY KEY (user_id, role_name)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS contributors_by_role
            ON contributors (role_name, display_name)
            """
        )


def synchronize_contributor(user_id, display_name, username, role_names):
    registered_at = discord.utils.utcnow().isoformat()
    rows = [
        (user_id, role_name, display_name, username, registered_at)
        for role_name in role_names
    ]

    with connect_contributor_database() as connection:
        connection.execute(
            "DELETE FROM contributors WHERE user_id = ?",
            (user_id,),
        )
        connection.executemany(
            """
            INSERT INTO contributors (
                user_id,
                role_name,
                display_name,
                username,
                registered_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )


def load_contributor_names():
    names_by_role = {role_name: [] for role_name in CREDIT_ROLE_NAMES}
    with connect_contributor_database() as connection:
        rows = connection.execute(
            """
            SELECT role_name, display_name
            FROM contributors
            ORDER BY role_name, display_name COLLATE NOCASE, user_id
            """
        ).fetchall()

    for role_name, display_name in rows:
        if role_name in names_by_role:
            names_by_role[role_name].append(display_name)
    return names_by_role


def registered_contributor_count():
    with connect_contributor_database() as connection:
        return connection.execute(
            "SELECT COUNT(DISTINCT user_id) FROM contributors"
        ).fetchone()[0]


def get_credit_roles(member):
    member_role_names = {role.name for role in member.roles}
    return [
        role_name
        for role_name in CREDIT_ROLE_NAMES
        if role_name in member_role_names
    ]


def build_credits_file(contributor_names):
    eight = "        "
    twelve = "            "
    sixteen = "                "
    sections = []

    for role_name in CREDIT_ROLE_NAMES:
        list_name = role_name.lower().replace(" ", "") + "s"
        names = contributor_names.get(role_name, [])

        lines = [eight + "$ " + list_name + " = ["]
        lines.extend(
            twelve + json.dumps(name, ensure_ascii=False) + ","
            for name in names
        )
        lines.extend(
            [
                eight + "]",
                eight + "vbox:",
                twelve
                + 'text "'
                + role_name
                + 's" size 80 color "#fff"',
                twelve + "for name in " + list_name + ":",
                sixteen + 'text name size 40 color "#fff"',
                "",
            ]
        )
        sections.append("\n".join(lines))

    return "\n".join(sections)


async def require_owner(interaction):
    if await bot.is_owner(interaction.user):
        return True

    await interaction.response.send_message(
        "Only the bot owner can use this command.",
        ephemeral=True,
    )
    return False


class PALBot(commands.Bot):
    async def setup_hook(self):
        initialize_contributor_database()

        # Register the persistent button before connecting, so buttons posted
        # during an earlier run continue working after a restart.
        self.add_view(ContributorRegistrationView())

        # These are global application commands. Discord can take some time to
        # display a newly-added global command after the first sync.
        await self.tree.sync()


intents = discord.Intents.default()
intents.members = False
intents.presences = False
intents.message_content = False

bot = PALBot(
    command_prefix=commands.when_mentioned,
    intents=intents,
)


class ContributorRegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Register for the Credits",
        style=discord.ButtonStyle.success,
        custom_id="palf:register_contributor",
        emoji="🎬",
    )
    async def register_contributor(self, interaction, button):
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "This button can only be used inside the PAL:F server.",
                ephemeral=True,
            )
            return

        eligible_roles = get_credit_roles(interaction.user)
        if not eligible_roles:
            await interaction.response.send_message(
                "You do not currently have a contributor role.",
                ephemeral=True,
            )
            return

        user_id = str(interaction.user.id)
        display_name = interaction.user.display_name

        async with contributor_lock:
            # Clicking again synchronizes a contributor with their current
            # credit roles, removing obsolete tiers and adding new ones.
            synchronize_contributor(
                user_id,
                display_name,
                interaction.user.name,
                eligible_roles,
            )

        role_list = ", ".join(eligible_roles)
        await interaction.response.send_message(
            f'You are registered as **{display_name}** under: {role_list}.',
            ephemeral=True,
        )


@bot.tree.command(
    name="post_contributor_registration",
    description="Post the persistent PAL:F contributor-registration button.",
)
@app_commands.describe(
    channel="The channel in which to post the registration message.",
)
async def post_contributor_registration(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
):
    if not await require_owner(interaction):
        return

    if interaction.guild is None:
        await interaction.response.send_message(
            "Use this command inside the PAL:F server.",
            ephemeral=True,
        )
        return

    target_channel = channel or interaction.channel
    if target_channel is None:
        await interaction.response.send_message(
            "I could not determine which channel to use.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="Register for the PAL:F Credits",
        description=(
            "If you have a contributor role, click the button below to add "
            "your current server display name to the PAL:F credits.\n\n"
            "You can click it again later to update your name or contributor tier."
        ),
        colour=0xE83E8C,
    )

    try:
        await target_channel.send(
            embed=embed,
            view=ContributorRegistrationView(),
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "I do not have permission to post in that channel.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Posted the contributor-registration button in {target_channel.mention}.",
        ephemeral=True,
    )

@bot.tree.command(
    name="reset_question_database",
    description="Clear every stored question-limiter record.",
)
@app_commands.describe(
    confirm="Confirm that every stored question record should be cleared.",
)
async def reset_question_database(
    interaction: discord.Interaction,
    confirm: bool = False,
):
    if not await require_owner(interaction):
        return

    if not confirm:
        await interaction.response.send_message(
            "Nothing was reset. Run the command again with `confirm` set to True.",
            ephemeral=True,
        )
        return

    cleared_count = len(questionlog)
    questionlog.clear()
    save_json(QUESTION_LOG_FILE, questionlog)

    await interaction.response.send_message(
        f"Cleared {cleared_count:,} stored question-limiter records.",
        ephemeral=True,
    )


@bot.tree.command(
    name="credits",
    description="Export the registered PAL:F contributors as Ren'Py code.",
)
async def credits(interaction: discord.Interaction):
    if not await require_owner(interaction):
        return

    contributor_names = load_contributor_names()
    credits_text = build_credits_file(contributor_names)
    contributor_count = registered_contributor_count()

    output = discord.File(
        io.BytesIO(credits_text.encode("utf-8")),
        filename="palf_contributors.rpy",
    )
    await interaction.response.send_message(
        f"Exported {contributor_count:,} registered contributors.",
        file=output,
        ephemeral=True,
    )


@bot.tree.command(
    name="poll",
    description="Create a weighted PAL:F storyline poll.",
)
@app_commands.describe(
    pollname="The title displayed on the poll.",
    storylines=(
        "Optional comma-separated storyline names. Leave blank to use every storyline."
    ),
)
async def poll(
    interaction: discord.Interaction,
    pollname: str = "Default Name Poll",
    storylines: Optional[str] = None,
):
    global polldata
    global activepollfile

    if not await require_owner(interaction):
        return

    if interaction.guild is None or interaction.channel is None:
        await interaction.response.send_message(
            "Use this command in a server text channel.",
            ephemeral=True,
        )
        return

    requested_storylines = []
    if storylines:
        requested_storylines = [
            storyline.strip()
            for storyline in storylines.split(",")
            if storyline.strip()
        ]

    if requested_storylines:
        storylines_by_casefold = {
            storyline.casefold(): storyline for storyline in emojipairs.values()
        }
        chosen_storylines = []
        missing_storylines = []
        for requested in requested_storylines:
            canonical = storylines_by_casefold.get(requested.casefold())
            if canonical is None:
                missing_storylines.append(requested)
            elif canonical not in chosen_storylines:
                chosen_storylines.append(canonical)

        if missing_storylines:
            await interaction.response.send_message(
                "Storylines not found: " + ", ".join(missing_storylines),
                ephemeral=True,
            )
            return

        chosen_emojipairs = {
            emoji: storyline
            for emoji, storyline in emojipairs.items()
            if storyline in chosen_storylines
        }
    else:
        chosen_emojipairs = dict(emojipairs)

    if not chosen_emojipairs:
        await interaction.response.send_message(
            "No valid storylines were selected.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    await interaction.channel.send(
        "# PAL:F Storyline Poll\n"
        "Use the reactions below to vote. Use /checkvote to privately "
        "check the status of your ballot."
    )

    number_of_storylines = len(chosen_emojipairs)
    embed_titles = (
        ["three", "two"]
        if number_of_storylines == 2
        else ["three", "two", "one"]
    )
    embeds = [
        discord.Embed(
            title=pollname,
            description=(
                f"Pick a storyline to give {title} "
                f"point{('s' if title != 'one' else '')} to."
            ),
            colour=0xFF0000,
        )
        for title in embed_titles
    ]

    for emoji, storyline in chosen_emojipairs.items():
        embeds[0].add_field(
            name=f"**{storyline}** - {emoji}",
            value="",
            inline=True,
        )

    poll_slug = re.sub(r"[^a-z0-9]+", "", pollname.casefold()) or "default"
    activepollfile = f"./databases/poll{poll_slug}.json"

    message_ids = []
    for embed in embeds:
        message = await interaction.channel.send(embed=embed)
        message_ids.append(message.id)
        for emoji in chosen_emojipairs:
            await message.add_reaction(emoji)

    poll_dictionary = {
        "messageids": message_ids,
        "votes": {},
        "point_levels": len(embed_titles),
        "storylines": list(chosen_emojipairs.values()),
    }

    async with poll_lock:
        polldata = {message_ids[0]: poll_dictionary}
        save_json(activepollfile, polldata)

    await interaction.followup.send(
        f'Created the poll "{pollname}".',
        ephemeral=True,
    )


@bot.tree.command(
    name="getcount",
    description="Show the current weighted poll totals.",
)
async def getcount(interaction: discord.Interaction):
    if not await require_owner(interaction):
        return

    if not polldata:
        await interaction.response.send_message(
            "There is no active poll.",
            ephemeral=True,
        )
        return

    poll_data = next(iter(polldata.values()))
    votes = poll_data["votes"]
    point_levels = poll_data["point_levels"]
    poll_storylines = poll_data.get("storylines", list(emojipairs.values()))
    total_votes = {storyline: 0 for storyline in poll_storylines}

    for ballot in votes.values():
        if (
            "3" in ballot
            and "2" in ballot
            and (point_levels != 3 or "1" in ballot)
        ):
            total_votes[ballot["3"]] += 3
            total_votes[ballot["2"]] += 2
            if point_levels == 3:
                total_votes[ballot["1"]] += 1

    poll_string = "```\n"
    for storyline, total in total_votes.items():
        poll_string += f"{total} - {storyline}\n"
    poll_string += "```"

    if activepollfile:
        async with poll_lock:
            save_json(activepollfile, polldata)

    await interaction.response.send_message(poll_string)


@bot.tree.command(
    name="checkvote",
    description="Privately check the status of your current poll ballot.",
)
async def checkvote(interaction: discord.Interaction):
    if not polldata:
        await interaction.response.send_message(
            "There is no active poll.",
            ephemeral=True,
        )
        return

    poll_data = next(iter(polldata.values()))
    votes = poll_data["votes"]
    point_levels = poll_data["point_levels"]
    user_id = str(interaction.user.id)

    lines = []
    if user_id in votes:
        ballot = votes[user_id]
        for points in range(4 - point_levels, 4):
            point_key = str(points)
            if point_key in ballot:
                lines.append(
                    f"You have given {points} "
                    f"point{'s' if points > 1 else ''} to {ballot[point_key]}."
                )
            else:
                lines.append(
                    f"You have not assigned your {points}-point vote yet."
                )

        if all(
            str(points) in ballot
            for points in range(4 - point_levels, 4)
        ):
            lines.append(
                "Voting is complete! Time to sit back and relax until the poll ends."
            )
    else:
        lines.append("You have not voted on the current poll.")

    await interaction.response.send_message(
        "\n".join(lines),
        ephemeral=True,
    )


@bot.event
async def on_ready():
    global questionlog

    loaded_questionlog = load_json(QUESTION_LOG_FILE, {})
    questionlog = {
        str(user_id): question_data
        for user_id, question_data in loaded_questionlog.items()
    }

    if not dumppolldata.is_running():
        dumppolldata.start()


@tasks.loop(seconds=10)
async def dumppolldata():
    if not activepollfile or not polldata:
        return

    async with poll_lock:
        save_json(activepollfile, polldata)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.channel_id not in POLL_CHANNEL_IDS:
        return

    member = payload.member
    if member is None or member.id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        return

    message = await channel.fetch_message(payload.message_id)

    master_message_id = None
    vote_index = None
    for key, poll_data in polldata.items():
        message_ids = poll_data["messageids"]
        if message.id in message_ids:
            master_message_id = key
            vote_index = 3 - message_ids.index(message.id)
            break

    if master_message_id is None:
        return

    poll_data = polldata[master_message_id]
    emoji = str(payload.emoji)
    storyline = emojipairs.get(emoji)
    allowed_storylines = set(
        poll_data.get("storylines", list(emojipairs.values()))
    )

    try:
        await message.remove_reaction(payload.emoji, member)
    except discord.Forbidden:
        pass

    if storyline is None or storyline not in allowed_storylines:
        return

    member_id = str(member.id)
    vote_key = str(vote_index)
    voting_complete = False

    async with poll_lock:
        votes = poll_data["votes"]
        now = datetime.now()

        if member_id not in votes:
            votes[member_id] = {
                "username": member.name,
                "lastvoted": now.strftime("%y-%m-%d %H:%M:%S.%f"),
                "accountmade": str(member.created_at),
            }
        else:
            last_voted = datetime.strptime(
                votes[member_id]["lastvoted"],
                "%y-%m-%d %H:%M:%S.%f",
            )
            if (now - last_voted).total_seconds() < 0.2:
                return
            votes[member_id]["lastvoted"] = now.strftime(
                "%y-%m-%d %H:%M:%S.%f"
            )
            votes[member_id]["username"] = member.name

        ballot = votes[member_id]
        for points in ("3", "2", "1"):
            if ballot.get(points) == storyline:
                del ballot[points]
                break

        ballot[vote_key] = storyline
        point_levels = poll_data["point_levels"]
        voting_complete = all(
            str(points) in ballot
            for points in range(4 - point_levels, 4)
        )

    if voting_complete:
        try:
            await member.send("Voting is complete! Thank you for your input.")
        except discord.Forbidden:
            pass


@bot.event
async def on_message(message):
    await limit_questions(message)


async def limit_questions(message):
    global questionlog

    if message.author.bot:
        return

    if await bot.is_owner(message.author):
        if message.reference and message.reference.message_id:
            try:
                old_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
            except (discord.NotFound, discord.Forbidden):
                return

            old_author_id = str(old_message.author.id)
            if old_author_id in questionlog:
                questionlog[old_author_id][4] = True
                save_json(QUESTION_LOG_FILE, questionlog)
        return

    if message.guild is None:
        return

    if message.channel.name not in QUESTION_CHANNEL_NAMES:
        return

    professor_role = get(message.guild.roles, name="Professor")
    member_roles = getattr(message.author, "roles", [])
    if professor_role is not None and professor_role in member_roles:
        return

    if message.author.name in QUESTION_EXEMPT_USERNAMES:
        return

    author_id = str(message.author.id)
    existing_question = questionlog.get(author_id)
    original_message = None

    if existing_question:
        year, month, day, message_id, responded = existing_question
        try:
            original_message = await message.channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            questionlog.pop(author_id, None)
            save_json(QUESTION_LOG_FILE, questionlog)

    if original_message is not None:
        year, month, day, message_id, responded = existing_question
        flavor1 = random.choice(
            [
                "Woah there, partner!",
                "Hold your horses!",
                "Hold on, buddy!",
                "Not so fast!",
                "Halt your actions!",
                "Stay thine hand!",
                "Sore wa chigau yo!",
                "Objection!",
                "Really? Right in front of my salad?",
                "Heaven or hell! Let's rock!",
                "Pray forgive the discourtesy, but you must be informed!",
                "Rulebreaker?!",
                "1,000 years dungeon!",
                "Be admonished!",
                "Abandon your course!",
                "psssh...nothin personnel...kid...",
                (
                    "Did someone just diddly-dang double post in this "
                    "goddang dev-questions server?"
                ),
                "That's a paddlin'.",
                "Right to jail!",
                "I've come to make an announcement:",
                "THIS COMMUNICATION IS NOT TOLERATED.",
                "¿Dos preguntas? ¿En esta economía?",
                "I sense heresy here...",
                (
                    "Never gonna give you up, but you better give up on "
                    "asking that question!"
                ),
                "HEY KIDS WANNA SEE A DEAD BODY?!",
                "Yaaaamerrroooo! YAAAAMMMMEEERRRROOOO!",
                (
                    "Death is not a hunter unbeknownst to its prey... "
                    "but this question's gotta be unbeknownst to you."
                ),
                (
                    "The #dev-questions is the means by which all is "
                    "revealed... but not _this_ question!"
                ),
                "I'm so goddamn tired.",
                "//FIX THIS: INSERT FUNNY QUOTE",
                "Keep doing that and I'll tell you about Homestuck.",
                "Assuming direct control.",
                "This hurts you.",
                "This kills the questioner.",
                (
                    "Allowance must be made for those who, without "
                    "concluding, continue questioning."
                ),
            ]
        )

        if (
            message.created_at.day == day
            and message.created_at.month == month
            and message.created_at.year == year
        ):
            flavor2 = random.choice(
                [
                    (
                        "Looks like you've already asked a question in "
                        "this channel today."
                    ),
                    "You can only ask one question in this channel a day!",
                    (
                        "Freud needs time to work on the actual game, and "
                        "the moderators need time to moderate! Please keep "
                        "your questions limited to one a day."
                    ),
                    "Two questions in a day... isn't that a bit much?",
                    (
                        "A thirst for knowledge is admirable, but give "
                        "Freud and the devs some time to work on, you know, "
                        "the _actual_ game!"
                    ),
                    (
                        "Freud and the devs love answering questions--"
                        "really--but there can be too much of a good thing! "
                        "Try to ask just one question a day, okay?"
                    ),
                    (
                        "If I had the time, I'd sit in front of "
                        "#dev-questions and answer all these questions, "
                        "non-stop. But I gotta spend _some_ time on the "
                        "game you're ostensibly here for."
                    ),
                    (
                        "Unlike Leaf, I'm a pretty good swimmer, but even I "
                        "can drown in questions! Try to limit it to one a "
                        "day, okay?"
                    ),
                    (
                        "Love the enthusiasm, but Freud and the devs have "
                        "limited time, and they spend _most_ of it on the "
                        "actual game, not #dev-questions. Mind limiting "
                        "your question-rate to one per day?"
                    ),
                ]
            )
            await message.reply(
                flavor1
                + " "
                + flavor2
                + " Your previous question is here: "
                + original_message.jump_url
            )
            return

        if not responded and original_message.id != message.id:
            flavor2 = random.choice(
                [
                    "Looks like Freud hasn't responded to your previous question yet!",
                    (
                        "Sorry to make you wait, but Freud hasn't gotten to "
                        "your previous question, yet."
                    ),
                    (
                        "Please give Freud a little more time to respond to "
                        "your previous question!"
                    ),
                    (
                        "Sorry, but Freud fell in a ditch somewhere, and "
                        "hasn't gotten around to answering your question "
                        "yet. Give him a bit!"
                    ),
                    (
                        "A thirst for knowledge is admirable, but give Freud "
                        "some time to answer your first question before you "
                        "come in asking about another one!"
                    ),
                    (
                        "Freud and the devs love answering questions--"
                        "really--but there can be too much of a good thing! "
                        "Give Freud some time to answer your first question "
                        "before asking another!"
                    ),
                    (
                        "If I had the time, I'd sit in front of "
                        "#dev-questions and answer all these questions, "
                        "non-stop. But I gotta spend _some_ time on the game "
                        "you're ostensibly here for, and that's why I "
                        "haven't been able to respond to your previous "
                        "question yet!"
                    ),
                    (
                        "Unlike Leaf, I'm a pretty good swimmer, but even I "
                        "can drown in questions! Please wait for me to "
                        "surface before pouring _more_ water over me!"
                    ),
                ]
            )
            await message.reply(
                flavor1
                + " "
                + flavor2
                + " Your previous question is here: "
                + original_message.jump_url
            )
            return

    questionlog[author_id] = [
        message.created_at.year,
        message.created_at.month,
        message.created_at.day,
        message.id,
        False,
    ]
    save_json(QUESTION_LOG_FILE, questionlog)


bot.run("TOKEN")
