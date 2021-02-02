import settings
import hikari
import lightbulb
from pymongo import MongoClient


# setup database
client = MongoClient(settings.CONNECTION_URL)
db = client['whistlebot-db']

# DATABASE EVENTS

def add_server(guild):
    print("hi")

bot = lightbulb.Bot(token=settings.DISCORD_BOT_TOKEN,
                    prefix='!',
                    insensitive_commands=True)

# flags a message by replying
@bot.command()
async def flag(ctx, reason=""):
    msg_type = str(ctx.message.type)
    if msg_type == 'DEFAULT':
        await ctx.respond('**error:** no message attached. please reply to the message you wish to flag!')
    elif msg_type == 'REPLY':
        msg_ref = ctx.message.referenced_message
        print(msg_ref.content)
        if msg_ref.author.id in [int(settings.DISCORD_CLIENT_ID)]:
            await ctx.respond('please do not attempt to circumvent whistlebot.')
        elif ctx.message.author.id == msg_ref.author.id:
            await ctx.respond('please do not attempt to abuse whistlebot functionality.')
        else:
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

bot.run()