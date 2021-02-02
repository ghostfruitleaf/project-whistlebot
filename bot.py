import settings
import discord
from pymongo import MongoClient
from discord.ext import commands  # for another class object

# setup database
client = MongoClient('mongodb://localhost:27017/')
db = client['whistlebot-db']

# declare intents
intents = discord.Intents.default()
intents.members = True


# cog for command version of discord bot
class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("pong")


# bot script
bot = commands.Bot(command_prefix='!', intents=intents)

bot.add_cog(Ping(bot))

bot.run(settings.DISCORD_BOT_TOKEN)
