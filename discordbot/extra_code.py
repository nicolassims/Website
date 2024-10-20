"""
@bot.command()
async def ping(ctx):
    await ctx.send("pong")

@bot.command()
async def getuser(ctx, role: discord.Role):
    fullstring = "["
    for mem in role.members:
        username = (mem.nick if mem.nick != None else str(mem))
        if ("[" in username):
            username = username.replace("[", "[[")
        quotemark = ('"' if "'" in username else '"')
        fullstring += quotemark + username + quotemark + ", "
    fullstring = fullstring[:-2] + "]"
    print(fullstring)
"""