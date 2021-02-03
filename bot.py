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


def add_server(guild):
    """
    add_server(guild)

    - accepts a discord Guild object to create a new server profile document in the database.
    - triggered through report from a server with no standing reports or through addition of
      server in user interface.
    - returns True if server profile added to database; False otherwise
    """
    server_doc = {'server_name': guild.name,  # name of server
                  'server_id': guild.id,  # server id
                  'auth_users': [guild.owner_id],  # users authorized to review reports
                  'auth_roles': [],  # roles authorized to review reports
                  'flagger_roles': [],  # roles authorized to flag messages
                  'flag_tags': [],  # tags to attach to reports
                  'member_count': guild.member_count,  # num of members for stats
                  'settings': {'kick_autoban': None,  # number of kicks that trigger an autoban
                               'autoban_flags': [],  # flags that trigger autobans - REQUIRES DOC/VALIDATION
                               'user_agrmt_req': False,  # initialize user agreement requirement
                               'user_agrmt_channel_id':
                                   guild.system_channel_id if not guild.system_channel_id is None else 0,
                               # channel for user agreement
                               'user_agrmt_message_id': None,  # message to check for agreement
                               'settings_roles': [],  # roles that can change server settings
                               'settings_users': [],  # roles that can change server users
                               'alert_roles': [],  # roles to be alerted of report
                               'alert_users': [],  # users to be alerted of report
                               'alert_channel_id': None  # id of channel to receive reports, if specified
                               }
                  }

    return True if db.servers.insert_one(server_doc).acknowledged else False


def save_reported_message(reported_message, report_id, reporter_id):
    """
    save_reported_message(reported_message)

    - creates and saves document for reported message as helper method of create_report.
    - does not create new reported_message if already in db, but increments times reported.
    - returns True, 1 if saved to/found in database, False, 0 otherwise
    - returns True, 0 if found in database but is a duplicate report (same user reports same message)
    - ^ this allows another way to increase the priority of reports
    """

    # grab the information first
    exhibit = {  # info of REPORTED MESSAGE
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
        'reports': [int(report_id)]  # reports made about message
    }

    # check database

    query = {'reported_message_id': int(reported_message.id)}
    find_exhibit = db.exhibits.find_one(query)
    # reported message exists; object is returned
    if find_exhibit is not None:

        # check to see if repeat reporter
        reporter_exists = False
        reports = find_exhibit['reports']

        for id_num in reports:
            if db.reports.find_one({'report_id': id_num, 'reporter_id': reporter_id}):
                reporter_exists = True
                break

        # don't update unless it's a new reporter
        if not reporter_exists:
            # new values
            rpt_times = find_exhibit['times_reported'] + 1
            reports = reports.append(int(report_id))
            update_val = {'$set': {'times_reported': rpt_times, 'reports': reports}}
            db.exhibits.update_one({'reported_message_id': int(reported_message.id)}, update_val)

        # tell reporter not to do that, please -- this should help prevent spam
        else:
            return True, 0
        return True, 1

    # add to db
    else:
        return (True, 1) if db.exhibits.insert_one(exhibit).acknowledged else (False, 0)


def create_report(report, reported_message):
    """
    create_report(report,reported_message)

    - creates report document in database using a message starting with !flag command
      and message that is replied to
    - triggered through authorized !flag command call from a user in a server
    - triggers creation of server document in database if not already existing
    - triggers creation of users if not already in database AFTER creation of report.
    """
    rptd_msg = save_reported_message(reported_message, report.id, report.author.id)  # get tuple code

    # no message saved successfully
    if rptd_msg[0] and rptd_msg[1] < 1:
        return None
    # message saved
    elif rptd_msg[0]:
        # generate report
        report_content = report.content.replace('!flag', '', 1)

        # find flags
        flags = []
        server_flags = db.servers.find_one({'server_id': int(report.guild_id)})

        for word in server_flags:
            if word in report_content.lower(): flags.append(word)

        # ALWAYS generate report if saved
        report = {'reviewed': [False, None],  # indicates if report has been reviewed and by who?
                  'action': {'auth_user_id': None,
                             'timestamp': '',
                             'action_taken': ''},  # resulting action taken and user id of person who did it
                  'server_id': report.guild_id,  # id of server message was sent in
                  'report_id': report.id,  # id of report message (in case of system abuse)
                  'report_time': report.timestamp,  # time of report
                  'reporter_id': report.author.id,  # id of reporter (for fast access)
                  'report_reason': report_content,  # reason for reporting
                  'flag_tags': flags,  # array of flags identified from reason text
                  'reported_message_id': reported_message.id
                  }

        if not db.reports.insert_one(report).acknowledged: return False
        # check that server is in database
        # check that both users are in database (needs finally)
        return True
    else:
        # indicates attempt to double report a message
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


def create_user_profile(user):
    new_admin = {

    }
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
    """
    Checks that servers that whistlebot is in has profiles in database.
    Creates new profile if one not currently found, or once whistlebot joins database.
    """
    # check if server is in db
    find_server = db.servers.find_one({'server_id': int(event.guild.id)})

    # get owner object in case message needed to send alert
    get_id = event.guild.owner_id
    owner = await bot.rest.fetch_user(user=get_id)

    # add new server profile to db
    if find_server is None:
        add_new_server = add_server(event.guild)

        # sends warning message that server profile was not added to system.
        if not add_new_server: await owner.send('whistlebot was unable to create a new profile for the following '
                                                f'server: {event.guild.name}. please try re-adding the bot or'
                                                'adding an issue at https://github.com/PaulineChane/project-whistlebot.')


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
    # default message: DM error if no reply found
    msg = '**no report sent!** please reply to a server message you wish to flag!'

    # handle various reply cases
    if msg_type == 'REPLY':

        # get reported message
        msg_ref = ctx.message.referenced_message

        # when/if implemented, flag authorization check

        # don't report the bot
        if msg_ref.author.id == int(settings.DISCORD_CLIENT_ID):  # do we need to check for an attempt to report a bot?
            msg = 'do not attempt to report the bot.'

        # trying to self-report or report a system user.
        elif ctx.message.author.id == msg_ref.author.id:
            msg = 'please do not attempt to abuse whistlebot functionality.'

        else:
            # below should only trigger if report is created
            rpt_success = create_report(ctx.message, msg_ref)

            if rpt_success is None:
                msg = 'we have already received your previous report on this message.'
            elif not rpt_success:
                msg = 'we were not able to create a report. please try again.'
            else:
                await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                msg = 'thank you for your report -- it is currently under review by the admin team.'

    # send msg
    await ctx.message.author.send("**whistlebot update!**\n" + msg)


# view status in server according to whistlebot


# help function customized, time permitting

# run bot
bot.run()
