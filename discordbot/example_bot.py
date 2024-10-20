import json
import discord
from datetime import datetime
from discord.ext import commands, tasks
from discord.utils import get

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot('!', intents=intents)

polldata = { }

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
        fullstring = "```" + eight + "$ " + listname + "s = ["
        for mem in role.members:
            username = (mem.nick if mem.nick != None else str(mem))
            if ("[" in username):
                username = username.replace("[", "[[")
            quotemark = ('"' if "'" in username else '"')
            fullstring += quotemark + username + quotemark + ", "
        await ctx.send(fullstring[:-2] + "]\n" + eight + 'vbox:' + "\n" + twelve + 'text "' + rolestring + 's" size 80 color "#fff"\n' + twelve + 'for name in ' + listname + 's:\n' + sixteen + 'text name size 40 color "#fff"```')

#@bot.event
#async def on_message(message):
#    if message.author.bot: #if message's author is a bot, then ignore it.
#        return
#
#    if (message.content == "What do you think?"):
#        await message.channel.send('That\'s a wonderful idea!')

emojipairs = {
    "⚔️" : "Rusted Swords",
    "❤️" : "The Shapes of Love",
    "👣" : "Stride Alone",
    "⭐" : "The Price of Fame",
    "🩹" : "A Whole Human",
    "⌛" : "Memories of A Future",
    "⚖️" : "The Laws of Night"
}

namepairs = {v: k for k, v in emojipairs.items()}

@bot.command()
async def poll(ctx):
    global polldata
    if (str(ctx.author) not in ["draymonddarksteel#0", "draymonddarksteel"]):
        return
    
    await ctx.send("# Please Temporarily Enable Server DMs to Use This Bot\n## Use `!checkvote` to check on the status of your vote.")
    embed1 = discord.Embed(title="Test Poll",
                            description=f'Pick a storyline to give three points to.',
                            colour=0xFF0000)
    
    for key, value in emojipairs.items():
        embed1.add_field(name="**" + value + "** - " + key, value="", inline=True)
    
    embed2 = discord.Embed(title="",
                            description=f'Pick a storyline to give two points to.',
                            colour=0xFF0000)
    
    embed3 = discord.Embed(title="",
                            description=f'Pick a storyline to give one point to.',
                            colour=0xFF0000)
    
    #options = 

    #embed.set_thumbnail(
    #    url=f'https://cdn.discordapp.com/icons/{ctx.message.guild.id}/{ctx.message.guild.icon}.png')

    #embed.add_field(name=embed.title, value=embed.description, inline=True)

    

    # Poll data
    with open('./databases/poll.json', 'r'):
        polldata = {}
        messageids = []
        for embed in [embed1, embed2, embed3]:
            message = await ctx.send(embed=embed)
            messageids.append(message.id)

            for item in ["⚔️", "❤️", "👣", "⭐", "🩹", "⌛", "⚖️"]:
                await message.add_reaction(item)

        poll_dictionary = { "messageids" : messageids, "votes" : {} }
        polldata[messageids[0]] = poll_dictionary

        with open('./databases/poll.json', 'w') as new_polldata:
            json.dump(polldata, new_polldata, indent=4)

@bot.command()
async def getcount(ctx):
    global polldata
    if (str(ctx.author) not in ["draymonddarksteel#0", "draymonddarksteel"]):
        return
    
    with open('./databases/poll.json', 'w') as update_polldata:
        json.dump(polldata, update_polldata, indent=4)
    
    #polldata = json.load(open('./databases/poll.json', 'r'))
    voteslist = list(polldata.values())[0]["votes"]

    totalvotes = {}
    for value in emojipairs.values():
        totalvotes[value] = 0
    
    for value in voteslist.values():
        if ('3' in value and '2' in value and '1' in value):
            totalvotes[value['3']] += 3
            totalvotes[value['2']] += 2
            totalvotes[value['1']] += 1

    pollstring = "```"
    for key, value in totalvotes.items():
        pollstring += str(value) + " - " + key  + "\n"
    pollstring += "```"

    await ctx.send(pollstring)

@bot.command()
async def checkvote(ctx):
    global polldata
    if (not (ctx.channel.type is discord.ChannelType.private or str(ctx.channel.name) in ["superadminchannel", "bots"])):
        correctchannel = bot.get_channel(1089705891265261598).mention
        await ctx.send("This isn't the right channel for this! Please go into " + correctchannel + ".")
        return
    
    #polldata = json.load(open('./databases/poll.json', 'r'))
    voteslist = list(polldata.values())[0]["votes"]

    pollstring = "```"
    user = str(ctx.author.id)
    if (user in voteslist):
        myvotes = voteslist[user]

        somethingmissing = False
        for i in range(1, 4):
            if (str(i) in myvotes):
                pollstring += "You have given " + str(i) + " point" + ("" if i == 1 else "s") + " to " + myvotes[str(i)] + ".\n"
            else:
                somethingmissing = True
                pollstring += "You have not assigned your " + str(i) + "-point vote yet.\n"
        
        if (not somethingmissing):
            pollstring += "Voting is complete! Time to sit back and relax 'til the polls end.\n"

    else:
        pollstring += "You have not voted on the current poll."

    pollstring += "```"

    channel = await ctx.author.create_dm()
    await channel.send(pollstring)

@bot.event
async def on_ready():
    await myLoop.start()


@tasks.loop(seconds = 10) # repeat after every 10 seconds
async def myLoop():
    global polldata
    with open('./databases/poll.json', 'w') as new_polldata:
        json.dump(polldata, new_polldata, indent=4)

@bot.event
async def on_raw_reaction_add(payload):
    global polldata
    if (payload.channel_id not in [1082467211291148351, 1092807840256766012, 1153733706821935125]):
        return
    
    member = payload.member
    memberid = member.id
    myid = bot.user.id#palf-discussion, announcements, superadminchannel
    if (memberid != myid):
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        #polldata = json.load(open('./databases/poll.json', 'r'))
        pollids = []
        mastermessageid = ""
        voteindex = 3
        for key, poll in polldata.items():
            messageids = poll["messageids"]
            pollids.extend(messageids)
            if (message.id in messageids):
                mastermessageid = key
                voteindex = 3 - messageids.index(message.id)
                
        if (message.id in pollids):
            poll = polldata[mastermessageid]
            votes = poll["votes"]
            memberstr = str(memberid)
            votestr = str(voteindex)
            #reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
            if (memberstr not in votes):
                votes[memberstr] = {"username" : member.name, "lastvoted" : str(datetime.now().strftime("%y-%m-%d %H:%M:%S.%f")), "accountmade" : str(member.created_at) }
            elif ((datetime.now() - datetime.strptime(votes[memberstr]["lastvoted"], '%y-%m-%d %H:%M:%S.%f')).total_seconds() < 0.2):
                return
                
            myvotes = votes[memberstr]
            emoji = str(payload.emoji)

            if (emoji not in emojipairs):
                await message.remove_reaction(payload.emoji, member)
                content = "Woopsie-daisy! Looks like you clicky-wicky'd on the wrong emoji-woji. UWU Want to try againsies?"
            else:
                content = ""
                storylinename = emojipairs[emoji]

                await message.remove_reaction(payload.emoji, member)

                if (storylinename in myvotes.values()):
                    preindex = 3
                    if ('2' in myvotes and myvotes['2'] == storylinename):
                        preindex = 2
                    elif ('1' in myvotes and myvotes['1'] == storylinename):
                        preindex = 1
                    del myvotes[str(preindex)]
                    content += "Removing your " + str(preindex) + "-point vote for " + storylinename + ". "

                myvotes[votestr] = storylinename

                content += "Your " + votestr + "-point vote for " + storylinename + " has been recorded."
                if ("3" not in myvotes):
                    content += " Please assign a 3-point vote to a storyline."
                elif ("2" not in myvotes):
                    content += " Please assign a 2-point vote to a storyline."
                elif ("1" not in myvotes):
                    content += " Please assign a 1-point vote to a storyline."
                else:
                    content += " Voting is complete! Pat yourself on the back for your grand contribution to democracy!"
            
            channel = await member.create_dm()
            await channel.send(content)
bot.run('Token')