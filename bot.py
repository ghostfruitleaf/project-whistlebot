"""
BOT.PY (@PaulineChane on GitHub)

command discord bot for project-whistlebot to create reports and track authorized interactions
with whistlebot on discord. primarily creates new entries for users, servers, and reports in database.
"""
import settings
import lightbulb
from pymongo import MongoClient

# setup database
client = MongoClient(settings.CONNECTION_URL)
db = client['whistlebot-db']

"""
DATABASE EVENT METHODS

creates new objects in whistlebot database.
"""

"""
add_server(guild)

- accepts a discord Guild object to create a new server profile document in the database. 
- triggered through report from a server with no standing reports or through addition of 
  server in user interface. 
"""


def add_server(guild):
    server_doc = {'doc_type': 'server',  # server doc
                  'server_name': guild.name,  # name of server
                  'server_id': int(guild.id),  # server id
                  'auth_users': [int(guild.owner_id)],  # users authorized to review reports
                  'auth_roles': [],  # roles authorized to review reports
                  'flagger_roles': [],  # roles authorized to flag messages
                  'flag_tags': [],  # tags to attach to reports
                  'member_count': guild.member_count,
                  'settings': {'kick_autoban': 0,  # number of kicks that trigger an autoban
                               'autoban_flags': [],  # flags that trigger autobans
                               'user_agrmt_req': False,  # initialize user agreement requirement
                               'user_agrmt_channel_id': int(guild.system_channel_id),  # channel for user agreement
                               'user_agrmt_message_id': 0  # message to check for agreement
                               }
                  }
    print(server_doc)


"""
create_report(report,reported_message)

- creates report document in database using a message starting with !flag command
  and message that is replied to 
- triggered through authorized !flag command call from a user in a server
- triggers creation of server document in database if not already existing
- triggers creation of users if not already in database AFTER creation of report. 
"""


def create_report(report, reported_message):
    # generate report
    report_content = report.content.replace('!flag ', '', 1)
    flags = []
    for word in report_content.split():
        # add word in flags if found in message contents
        print(word)

    report = {'doc_type': 'report',
              'read': False,
              'action': '',
              'server_id': report.guild_id,
              'report_id': report.id,
              'report_time': report.timestamp,
              'reporter_user': report.author,
              'reporter_user_id': report.author.id,
              'report_reason': report_content,
              'flags': flags,
              'reported_message': {
                  'reported_user': reported_message.author,
                  'reported_user_id': reported_message.author.id,
                  'reported_message': reported_message.content,
                  'reported_embed': reported_message.embeds,
                  'reported_attachments': reported_message.attachments,
                  'reported_timestamp': reported_message.timestamp,
                  'reported_edited_timestamp': reported_message.edited_timestamp,
              }
              }
    print(report)
    # check that server is in database
    # check that both users are in database (needs finally)


def create_member_doc(member):
    member = {}
    print(member)


def create_user_profile(member):
    user = {}
    print(user)


# initialize bot
bot = lightbulb.Bot(token=settings.DISCORD_BOT_TOKEN,
                    prefix='!',
                    insensitive_commands=True)


# flags a message by replying
@bot.command()
async def flag(ctx):
    msg_type = str(ctx.message.type)
    if msg_type == 'DEFAULT':
        await ctx.message.author.send('**no report sent!** no message attached -- please reply to the message you wish to flag!')
    elif msg_type == 'REPLY':
        msg_ref = ctx.message.referenced_message
        print(msg_ref.content)
        if msg_ref.author.id in [
            int(settings.DISCORD_CLIENT_ID)]:  # do we need to check for an attempt to report a bot?
            await ctx.message.author.send('please do not attempt to circumvent whistlebot.')
        elif ctx.message.author.id == msg_ref.author.id:
            await ctx.message.author.send('please do not attempt to abuse whistlebot functionality.')
        else:
            await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

@bot.command()
async def ping(ctx):
    await ctx.message.author.send('pong')

# run bot
bot.run()
