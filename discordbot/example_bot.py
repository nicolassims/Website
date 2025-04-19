import json
import discord
import random
from datetime import datetime
from discord.ext import commands, tasks
from discord.utils import get
from asyncio import Lock

lock = Lock()

intents = discord.Intents.default()
intents.members = True
intents.messages = True

bot = commands.Bot('!', intents=intents)

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
    "⚖️": "The Laws of Night"
}

namepairs = {v: k for k, v in emojipairs.items()}

@bot.command()
async def credits(ctx):
    if (str(ctx.author) not in ["draymonddarksteel#0", "draymonddarksteel"]):
        return

    eight = "        "
    twelve = "            "
    sixteen = "                "
    fullstring = ""
    rolestrings = ["Teaching Assistant", "Top Student", "Commissioner"]
    for rolestring in rolestrings:
        role = get(ctx.guild.roles, name=rolestring)
        listname = role.name.lower().replace(" ", "")
        fullstring += eight + "$ " + listname + "s = ["
        for mem in role.members:
            username = (mem.nick if mem.nick != None else str(mem))
            if ("[" in username):
                username = username.replace("[", "[[")
            quotemark = ('"' if "'" in username else '"')
            fullstring += quotemark + username + quotemark + ", "
            if (len(fullstring) > 1800):
                await ctx.send("```" + fullstring + "```")
                fullstring = ""
        fullstring = fullstring[:-2] + "]\n" + eight + 'vbox:' + "\n" + twelve + 'text "' + rolestring + 's" size 80 color "#fff"\n' + twelve + 'for name in ' + listname + 's:\n' + sixteen + 'text name size 40 color "#fff"\n\n'
        await ctx.send("```" + fullstring + "```")
        fullstring = ""

@bot.command()
async def poll(ctx, pollname = "Default Name Poll", *storylines):
    global polldata
    global activepollfile

    if (str(ctx.author) not in ["draymonddarksteel#0", "draymonddarksteel"]):
        return
    
    if not pollname:
        await ctx.send("You must provide a name for the poll.")
        return

    # Filter storylines to the specified ones, or use all if none specified
    if storylines:
        chosen_emojipairs = {k: v for k, v in emojipairs.items() if v in storylines}
        missing_storylines = set(storylines) - set(chosen_emojipairs.values())
        if missing_storylines:
            await ctx.send(f"Storylines not found: {', '.join(missing_storylines)}")
    else:
        chosen_emojipairs = emojipairs

    if not chosen_emojipairs:
        await ctx.send("No valid storylines provided for the poll.")
        return

    await ctx.send("# Please Temporarily Enable Server DMs to Use This Bot\n## Use `!checkvote` to check on the status of your vote.")

    # Decide which embeds to use based on the number of storylines
    num_storylines = len(chosen_emojipairs)
    embed_titles = ["three", "two"] if num_storylines == 2 else ["three", "two", "one"]
    embeds = [
        discord.Embed(
            title=pollname,
            description=f"Pick a storyline to give {title} point{('s' if title != 'one' else '')} to.",
            colour=0xFF0000
        )
        for title in embed_titles
    ]

    # Populate each embed with the chosen storylines
    #for embed in embeds:
    for key, value in chosen_emojipairs.items():
        embeds[0].add_field(name="**" + value + "** - " + key, value="", inline=True)

    activepollfile = './databases/poll' + pollname.replace(" ", "").lower() + '.json'

    with open(activepollfile, 'w') as file:
        file.write('{}')
        file.close()

    # Sending poll embeds with reactions
    with open(activepollfile, 'r'):
        polldata = {}
        messageids = []
        for embed in embeds:
            message = await ctx.send(embed=embed)
            messageids.append(message.id)
            for emoji in chosen_emojipairs:
                await message.add_reaction(emoji)

        poll_dictionary = {"messageids": messageids, "votes": {}, "point_levels": len(embed_titles)}
        polldata[messageids[0]] = poll_dictionary

        with open(activepollfile, 'w') as new_polldata:
            json.dump(polldata, new_polldata, indent=4)

@bot.command()
async def getcount(ctx):
    global polldata
    if (str(ctx.author) not in ["draymonddarksteel#0", "draymonddarksteel"]):
        return

    with open(activepollfile, 'w') as update_polldata:
        json.dump(polldata, update_polldata, indent=4)

    voteslist = list(polldata.values())[0]["votes"]
    point_levels = list(polldata.values())[0]["point_levels"]

    totalvotes = {value: 0 for value in emojipairs.values()}

    for value in voteslist.values():
        if '3' in value and '2' in value and (point_levels != 3 or '1' in value):
            totalvotes[value['3']] += 3
            totalvotes[value['2']] += 2
            if point_levels == 3 and '1' in value:
                totalvotes[value['1']] += 1

    pollstring = "```"
    for key, value in totalvotes.items():
        pollstring += f"{value} - {key}\n"
    pollstring += "```"

    await ctx.send(pollstring)

@bot.command()
async def checkvote(ctx):
    global polldata
    if not (ctx.channel.type is discord.ChannelType.private or str(ctx.channel.name) in ["superadminchannel", "bots"]):
        correctchannel = bot.get_channel(1089705891265261598).mention
        await ctx.send("This isn't the right channel for this! Please go into " + correctchannel + ".")
        return

    voteslist = list(polldata.values())[0]["votes"]
    point_levels = list(polldata.values())[0]["point_levels"]

    pollstring = "```"
    user = str(ctx.author.id)
    if user in voteslist:
        myvotes = voteslist[user]
        for i in range(4 - point_levels, 4):
            if str(i) in myvotes:
                pollstring += f"You have given {i} point{'s' if i > 1 else ''} to {myvotes[str(i)]}.\n"
            else:
                pollstring += f"You have not assigned your {i}-point vote yet.\n"
        
        if all(str(i) in myvotes for i in range(4 - point_levels, 4)):
            pollstring += "Voting is complete! Time to sit back and relax 'til the polls end.\n"

    else:
        pollstring += "You have not voted on the current poll."

    pollstring += "```"
    channel = await ctx.author.create_dm()
    await channel.send(pollstring)

@bot.event
async def on_ready():
    global questionlog
    questionlog = json.loads(open('./databases/questionlog.json', 'r').read())
    await dumppolldata.start()

@tasks.loop(seconds = 10) # repeat after every 10 seconds
async def dumppolldata():
    global polldata

    async with lock:
        with open(activepollfile, 'w') as new_polldata:
            json.dump(polldata, new_polldata, indent=4)

@bot.event
async def on_raw_reaction_add(payload):
    global polldata
    if payload.channel_id not in [1082467211291148351, 1092807840256766012, 1153733706821935125]:
        return

    member = payload.member
    memberid = member.id
    myid = bot.user.id
    if memberid != myid:
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        pollids = []
        mastermessageid = ""
        voteindex = 3

        for key, poll in polldata.items():
            messageids = poll["messageids"]
            pollids.extend(messageids)
            if message.id in messageids:
                mastermessageid = key
                voteindex = 3 - messageids.index(message.id)

        if message.id in pollids:
            poll = polldata[mastermessageid]
            votes = poll["votes"]
            point_levels = poll["point_levels"]
            memberstr = str(memberid)
            votestr = str(voteindex)

            if memberstr not in votes:
                votes[memberstr] = {"username": member.name, "lastvoted": str(datetime.now().strftime("%y-%m-%d %H:%M:%S.%f")), "accountmade": str(member.created_at)}
            elif (datetime.now() - datetime.strptime(votes[memberstr]["lastvoted"], '%y-%m-%d %H:%M:%S.%f')).total_seconds() < 0.2:
                return

            myvotes = votes[memberstr]
            emoji = str(payload.emoji)

            if emoji not in emojipairs:
                await message.remove_reaction(payload.emoji, member)
            else:
                storylinename = emojipairs[emoji]
                await message.remove_reaction(payload.emoji, member)

                if storylinename in myvotes.values():
                    preindex = 3
                    if '2' in myvotes and myvotes['2'] == storylinename:
                        preindex = 2
                    elif '1' in myvotes and myvotes['1'] == storylinename:
                        preindex = 1
                    del myvotes[str(preindex)]

                myvotes[votestr] = storylinename

                if all(str(i) in myvotes for i in range(4 - point_levels, 4)):
                    channel = await member.create_dm()
                    await channel.send("Voting is complete! Thank you for your input.")

@bot.event
async def on_message(message):
    await limit_questions(message)

    await bot.process_commands(message)

async def limit_questions(message):
    global questionlog

    if ("draymonddarksteel" in message.author.name):
        if (message.reference and message.reference.message_id):
            old_message = await message.channel.fetch_message(message.reference.message_id)
            if (old_message.author.id in questionlog):
                questionlog[old_message.author.id][4] = True#4 is the 'true' parameter
                with open('./databases/questionlog.json', 'w') as new_questiondata:
                    json.dump(questionlog, new_questiondata, indent=4)
        return

    if (message.channel.name not in ["superadminchannel", "dev-questions"] or message.author.bot or discord.utils.find(lambda r: r.name == 'Professor', message.guild.roles) in message.author.roles or "maslina8" in message.author.name or "mmcc_94868" in message.author.name):
        return

    if (message.author.id in questionlog):
        year, month, day, id, responded = questionlog[message.author.id]
        original_message = await message.channel.fetch_message(id)
        flavor1 = random.choice(["Woah there, partner!", "Hold your horses!", "Hold on, buddy!", "Not so fast!", "Halt your actions!", "Stay thine hand!", "Sore wa chigau yo!", "Objection!", "Really? Right in front of my salad?", "Heaven or hell! Let's rock!", "Pray forgive the discourtesy, but you must be informed!", "Rulebreaker?!", "1,000 years dungeon!", "Be admonished!", "Abandon your course!", "psssh...nothin personnel...kid...", "Did someone just diddly-dang double post in this goddang dev-questions server?", "That's a paddlin'.", "Right to jail!", "I've come to make an announcement:", "THIS COMMUNICATION IS NOT TOLERATED.", "¿Dos preguntas? ¿En esta economía?", "I sense heresy here...", "Never gonna give you up, but you better give up on asking that question!", "HEY KIDS WANNA SEE A DEAD BODY?!", "Yaaaamerrroooo! YAAAAMMMMEEERRRROOOO!", "Death is not a hunter unbeknownst to its prey... but this question's gotta be unbeknownst to you.", "The #dev-questions is the means by which all is revealed... but not _this_ question!", "I'm so goddamn tired.", "//FIX THIS: INSERT FUNNY QUOTE", "Keep doing that and I'll tell you about Homestuck.", "Assuming direct control.", "This hurts you.", "This kills the questioner.", "Allowance must be made for those who, without concluding, continue questioning."])
        if (message.created_at.day == day and message.created_at.month == month and message.created_at.year == year):
            flavor2 = random.choice(["Looks like you've already asked a question in this channel today.", "You can only ask one question in this channel a day!", "Freud needs time to work on the actual game, and the moderators need time to moderate! Please keep your questions limited to one a day.", "Two questions in a day... isn't that a bit much?", "A thirst for knowledge is admirable, but give Freud and the devs some time to work on, you know, the _actual_ game!", "Freud and the devs love answering questions--really--but there can be too much of a good thing! Try to ask just one question a day, okay?", "If I had the time, I'd sit in front of #dev-questions and answer all these questions, non-stop. But I gotta spend _some_ time on the game you're ostensibly here for.", "Unlike Leaf, I'm a pretty good swimmer, but even I can drown in questions! Try to limit it to one a day, okay?", "Love the enthusiasm, but Freud and the devs have limited time, and they spend _most_ of it on the actual game, not #dev-questions. Mind limiting your question-rate to one per day?"])
            await message.reply(flavor1 + " " + flavor2 + " Your previous question is here: " + original_message.jump_url)
            return
        
        elif (not responded and not original_message.id == message.id):
            flavor2 = random.choice(["Looks like Freud hasn't responded to your previous question yet!", "Sorry to make you wait, but Freud hasn't gotten to your previous question, yet.", "Please give Freud a little more time to respond to your previous question!", "Sorry, but Freud fell in a ditch somewhere, and hasn't gotten around to answering your question yet. Give him a bit!", "A thirst for knowledge is admirable, but give Freud some time to answer your first question before you come in asking about another one!", "Freud and the devs love answering questions--really--but there can be too much of a good thing! Give Freud some time to answer your first question before asking another!", "If I had the time, I'd sit in front of #dev-questions and answer all these questions, non-stop. But I gotta spend _some_ time on the game you're ostensibly here for, and that's why I haven't been able to respond to your previous question yet!", "Unlike Leaf, I'm a pretty good swimmer, but I even I can drown in questions! Please wait for me to surface before pouring _more_ water over me!"])
            await message.reply(flavor1 + " " + flavor2 + " Your previous question is here: " + original_message.jump_url)
            return

    questionlog[message.author.id] = [message.created_at.year, message.created_at.month, message.created_at.day, message.id, False]
    with open('./databases/questionlog.json', 'w') as new_questiondata:
        json.dump(questionlog, new_questiondata, indent=4)

bot.run('Token')