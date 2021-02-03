"""
BOT.PY (@PaulineChane on GitHub)

command discord bot for project-whistlebot to create reports and track authorized interactions
with whistlebot on discord. primarily creates new entries for users, servers, and reports in database.
"""
import settings
import hikari
import lightbulb
from pymongo import MongoClient

# setup database
client = MongoClient(settings.CONNECTION_URL)
db = client['whistlebot-db']

"""
DATABASE EVENT METHODS

creates new objects in whistlebot database.
"""


# NOTE: NEEDS TO BE SECURED SOMEHOW??? HTTPS CONNECTION MAYBE?
def add_server(guild):
    """
    add_server(guild)

    - accepts a discord Guild object to create a new server profile document in the database.
    - triggered through report from a server with no standing reports or through addition of
      server in user interface.
    - returns True if server profile added to database; false otherwise
    """
    server_doc = {'doc_type': 'server',  # server doc
                  'server_name': guild.name,  # name of server
                  'server_id': int(guild.id),  # server id
                  'auth_users': [int(guild.owner_id)],  # users authorized to review reports
                  'auth_roles': [],  # roles authorized to review reports
                  'flagger_roles': [],  # roles authorized to flag messages
                  'flag_tags': [],  # tags to attach to reports
                  'member_count': guild.member_count,  # num of members for stats
                  'settings': {'kick_autoban': None,  # number of kicks that trigger an autoban
                               'autoban_flags': [],  # flags that trigger autobans - REQUIRES DOC/VALIDATION
                               'user_agrmt_req': False,  # initialize user agreement requirement
                               'user_agrmt_channel_id': int(guild.system_channel_id) if not guild.system_channel_id is None else 0,  # channel for user agreement
                               'user_agrmt_message_id': None,  # message to check for agreement
                               'settings_roles': [],  # roles that can change server settings
                               'settings_users': [],  # roles that can change server users
                               'alert_roles': [],  # roles to be alerted of report
                               'alert_users': [],  # users to be alerted of report
                               'alert_channel_id': None  # id of channel to receive reports, if specified
                               }
                  }
    return True


def save_reported_message(reported_message, report_id, reporter_id):
    """
    save_reported_message(reported_message)

    - creates and saves document for reported message as helper method of create_report.
    - does not create new reported_message if already in db, but increments times reported.
    - returns True if saved to/found in database, False otherwise
    - ^ this allows another way to increase the priority of reports
    """
    # if reported message in database it is not yet, increment times_reported and add report id to reports[]
    # add check if a message is already reported
    # else
    reported_message = {  # info of REPORTED MESSAGE (should this be separated into another doc?)
        'doc_type': 'reported_message',
        'reported_message_id': reported_message.id,
        'reported_user_id': reported_message.author.id,  # id of reported user (access)
        'reported_message': reported_message.content,  # content of ORIGINAL reported message
        'reported_embed': [o.url for o in reported_message.embeds],  # any embeds in message (NEED ARRAY OF OBJECTS)
        'reported_attachments': [o.url for o in reported_message.attachments],
        # any attachments in message (NEED ARRAY OF OBJECTS)
        'reported_timestamp': reported_message.timestamp,  # time message sent
        'reported_edited_timestamp': reported_message.edited_timestamp,  # check for edit attempts
        'reported_edits': [] if reported_message.edited_timestamp is None else [reported_message.content],
        # array of edited messages as detected by bot on checks
        'deleted': False,  # confirms if message is deleted
        'times_reported': 1,
        'reports': [report_id]
    }

    print(reported_message)
    return True


def create_report(report, reported_message):
    """
    create_report(report,reported_message)

    - creates report document in database using a message starting with !flag command
      and message that is replied to
    - triggered through authorized !flag command call from a user in a server
    - triggers creation of server document in database if not already existing
    - triggers creation of users if not already in database AFTER creation of report.
    """
    # generate report
    report_content = report.content.replace('!flag ', '', 1)
    flags = []
    # server_flags = get from DB
    # for word in flags:
    #     # add word in flags if found in message contents
    #     # via substring

    # report layout
    if save_reported_message(reported_message, report.id, report.author.id):

        # ALWAYS generate report if saved
        report = {'doc_type': 'report',  # indicates REPORT
                  'reviewed': [False, 0],  # indicates if report has been reviewed and by who?
                  'action': {'auth_user_id': 0,
                             'timestamp': '',
                             'action_taken': ''},  # resulting action taken and user id of person who did it
                  'server_id': report.guild_id,  # id of server message was sent in
                  'report_id': report.id,  # id of report message (in case of system abuse)
                  'report_time': report.timestamp,  # time of report
                  'reporter_user_id': report.author.id,  # id of reporter (for fast access)
                  'report_reason': report_content,  # reason for reporting
                  'flags': flags,  # array of flags identified from reason text
                  'reported_message_id': reported_message.id
                  }
        print(report)
        # check that server is in database
        # check that both users are in database (needs finally)
        return True
    else:
        return False


def create_member_doc(member, reports=0):
    # info needed(?):
    # - id
    # - name
    # - servers
    # per server:
    # - status (left, kicked, banned, etc.)
    # - nickname(s)
    # - roles
    # - user agreement tuple/pair ("signed agreement"/"admin approved", need both to flag)
    # - num times attempted to flag when not allowed
    # - total reports by server (dict)
    # - array of report ids?????
    # - actions hash, tuples/pairs with # + reasons
    # - all flags
    # - server/notes hash -- yeah we might need a giant hash for all this :(
    # - avatar url (API call)
    # - deleted?
    member = {}
    print(member)


def create_user_profile(member):
    # info needed:
    # - id
    # - name
    # - owned servers (API call)
    # - authorized servers (narrow from API call and database info) - should have keys of permissions in UI
    # - way to link to member doc?? do they need one?
    # - reference roles in server profile per server, might need a dict?
    user = {}
    print(user)


"""
DATABASE CHECK METHODS

ensures all users, reports, servers documented in database. 
may need to optimize as an ensure function? 
"""

"""
DISCORD BOT/METHODS

ensures all users, reports, servers documented in database. 
may need to optimize as an ensure function? 
"""

# initialize bot
bot = lightbulb.Bot(token=settings.DISCORD_BOT_TOKEN,
                    prefix='!',
                    insensitive_commands=True)

"""
EVENT LISTENERS
"""


@bot.listen(hikari.GuildAvailableEvent)
async def check_server_profile(event):
    print(add_server(event.guild))


"""
COMMANDS
"""


# flags a message by replying
@lightbulb.guild_only()
@bot.command()
async def flag(ctx):
    """
    Reply to a server message with !flag in order to report it.
    Please note server moderation may require extra steps before you can use this function.
    """
    msg_type = str(ctx.message.type)  # ensure the message is a reply

    # DM error if no reply found
    if msg_type == 'DEFAULT':
        await ctx.message.author.send(
            '**no report sent!** no message attached -- please reply to the message you wish to flag!')

    # handle various reply cases
    elif msg_type == 'REPLY':

        # get reported message
        msg_ref = ctx.message.referenced_message
        print(msg_ref.content)  # debug statement

        # when/if implemented, flag authorization check
        # parameters for attempt to retaliate against a report?

        # not sure about this one yet -- reporting mods in retaliation?
        if msg_ref.author.id in [
            int(settings.DISCORD_CLIENT_ID)]:  # do we need to check for an attempt to report a bot?
            await ctx.message.author.send(
                'should people be allowed to report mods/admins/owners?')  # CHANGE MESSAGE!?!?!?

        # trying to self-report or report a system user.
        elif ctx.message.author.id == msg_ref.author.id:
            await ctx.message.author.send('please do not attempt to abuse whistlebot functionality.')

        else:
            # below should only trigger if report is created
            if create_report(ctx.message, msg_ref):
                await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                await ctx.message.author.send(
                    'thank you for your report -- it is currently under review by the admin team.')


# help function

# view list of flags

# view status in server according to whistlebot

# DM user test
@bot.command()
async def ping(ctx):
    """
    Test function.
    """
    await ctx.message.author.send('pong')


# run bot
bot.run()
