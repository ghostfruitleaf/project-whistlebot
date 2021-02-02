"""
BOT.PY

command discord bot for project-whistlebot
"""
import settings
import lightbulb
from pymongo import MongoClient



# setup database
client = MongoClient(settings.CONNECTION_URL)
db = client['whistlebot-db']

# DATABASE EVENT METHODS

def add_server(guild):
    server_doc = {'doc_type': 'server', # server doc
                  'server_name': guild.name, # name of server
                  'server_id': int(guild.id), # server id
                  'auth_users': [int(guild.owner_id)], # users authorized to review reports
                  'auth_roles': [], # roles authorized to review reports
                  'flagger_roles': [], # roles authorized to flag messages
                  'flag_tags': [], # tags to attach to reports
                  'member_count': guild.member_count,
                  'settings': {'kick_autoban': 0, # number of kicks that trigger an autoban
                               'autoban_flags': [], # flags that trigger autobans
                               'user_agrmt_channel_id': int(guild.system_channel_id), # channel for user agreement
                               'user_agrmt_message_id': 0 # message to check for agreement
                               }
                  }
    print(server_doc)

def create_report(report, reported_message, reason):
    report = {'doc_type': 'report',
              'server_id': report.guild_id,
              'report_id': report.id,
              'report_time': report.timestamp,
              'reporter_user': report.author,
              'report_reason': report.content.replace('!flag ',''),
              'flags': [],
              'reported_message':{

              }
              }
    print(report)

def create_member_doc(member):
    member = {}
    print(member)

def create_user_profile(member):
    user = {}
    print(user)

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