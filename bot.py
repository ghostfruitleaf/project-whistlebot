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


def generate_exhibit(reported_message, report_id):
    """
    generates exhibit doc to add to db
    """
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

    return exhibit


def save_reported_message(reported_message, report_id, reporter_id):
    """
    - creates and saves document for reported message as helper method of create_report.
    - does not create new reported_message if already in db, but increments times reported.
    - returns True, 1 if saved to/found in database, False, 0 otherwise
    - returns True, 0 if found in database but is a duplicate report (same user reports same message)
    - ^ this allows another way to increase the priority of reports
    """

    # grab the information first
    exhibit = generate_exhibit(reported_message, report_id)

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

        # flag to tell reporter not re-report a message, please -- this should help prevent spam
        else:
            return True, 0
        return True, 1

    # add to db
    else:
        return (True, 1) if db.exhibits.insert_one(exhibit).acknowledged else (False, 0)


def generate_report(report, report_content, flags, reported_message):
    """
    creates new report to save to db
    """
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
    return report


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
        new_report = generate_report(report, report_content, flags, reported_message)

        if not db.reports.insert_one(new_report).acknowledged: return False
        # check that server is in database
        # check that both users are in database (needs finally)
        return True
    else:
        # indicates attempt to double report a message
        return False


def generate_member_profile(user, member, guild, report_status=0):
    """
    generates new member_profile to save to db
    """
    new_member = {'server_id': guild.id,  # guild id
                  'user_id': user.id,  # user id of member
                  'reports_received': 1 if report_status == 1 else 0,
                  'reports_sent': 1 if report_status < 0 else 0,
                  'user_argmt_status': None,  # this is activated via interface
                  'server_status': 'active',  # this field needs to come from a tuple constant eventually
                  'nicknames': [member.nickname],  # start tracking nicknames
                  'roles': member.role_ids,  # all roles of member
                  'notes': ''
                  }
    return new_member


def ensure_member_profile(user, member, guild, report_status=0):
    """
    For a provided user (likely a recently reported/reporting user),
    ensures an existing member profile doc for a provided guild.

    PRECONDITIONS: user exists in database, user is same as member

    This will include information such as:
        - Number of reports received
        - Number of reports made
        - Current status (kicked, banned, left, active, etc.)
        - User agreement status (if enabled by mods)
        - Nicknames in server
        - Notes (for admin purposes)
        - Roles

    Returns True if successfully found/created/updated, False if there are database issues

    report_status codes: (FOR RECONFIG IN LATER RELEASE)
        0 - no report, maintenance only
        1 - report made against user
        -1 - report made by user
    """
    # verify user has guild profile
    query = {'server_id': int(guild.id), 'user_id': int(user.id)}
    find_member = db.member_profiles.find_one(query)

    # create new member profile
    if find_member is None:
        new_member = generate_member_profile(user, member, guild, report_status)

        # first ensure profile is added
        if not db.member_profiles.insert_one(new_member).acknowledged: return False

        # since user exists, we need to update the user object with a query to the new profile
        get_user = db.discordusers.find_one({'discord_id': int(user.id)})
        get_user['profiles'].append(query)
        db.discordusers.update_one({'discord_id': int(user.id)}, {"$set": {'profiles': get_user['profiles']}})

    else:  # profile exists
        if report_status == 0: return True  # do nothing if this was not initiated by a report

        # update with new report counts
        update_dict = {}
        if report_status == 1:
            update_dict = {'reports_received': find_member['reports_received'] + 1}
        elif report_status < 0:
            update_dict = {'reports_sent': find_member['reports_sent'] + 1}

        if report_status != 0:
            return True if db.member_profiles.update_one(query, {"$set": update_dict}).acknowledged else False


def update_user_doc(user, member, guild, report_status=0):
    """
    Accepts a user and ensures user is in database.
    Ensures that user has a profile associated with context guild (from calling guild-only bot methods)
    Returns:
        True, True: user and member_profile ensured
        True, False: only member_profile ensured
        False, True: only member ensured
        False, False: user and member_profile NOT ensured

    report_status codes: (FOR RECONFIG IN LATER RELEASE)
        0 - no report, maintenance only
        1 - report made against user
        -1 - report made by user
    """

    # first check for user
    get_user = db.discordusers.find_one({'discord_id': user.id})
    user_exists = False
    # create new user profile
    if get_user is None:
        new_user = {'discord_id': user.id,
                    'profiles': [{'server_id': guild.id, 'user_id': user.id}],  # add query just for guild the
                    # request came from for now
                    'deleted': False,  # we have other ways to confirm this info
                    'alts': []  # eventually there will be logic added to identify alts for accts
                    }
        added_user = db.discordusers.insert_one(new_user)

        if added_user.acknowledged:
            user_exists = True
    else:
        user_exists = True

    # update/create member
    profile_exists = True if ensure_member_profile(user, member, guild, report_status) else False

    return user_exists, profile_exists  # tuple code for updates


"""
DATABASE CHECK METHODS

ensures all users, reports, servers documented in database. 
may need to optimize as an ensure function? 
"""


def post_report_users_update(reporter_check, reported_check):
    """
    Prepares message to send to guild owner in event of save failure.
    Helper method for generating user/guild member profiles upon a report
    """
    msg = ""
    if not reporter_check[0]: msg += "reporting user info failed to save!\n"
    if not reporter_check[1]: msg += "reporting user member info failed to save!\n"
    if not reported_check[0]: msg += "reported user info failed to save!\n"
    if not reported_check[1]: msg += "reported user member info failed to save!\n"

    return "" if not msg else "**whistlebot update!**\n" + msg


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
MISC. ASYNC FUNCTIONS
"""

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
            msg = 'do not attempt to report whistlebot.'

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
                msg += f"\nif you wish to see status updates of your report, please type **!report_update {ctx.message.id}.**"

        # send msg
        await ctx.message.author.send("**whistlebot update!**\n" + msg)

        # get guild
        guild = await bot.rest.fetch_guild(guild=ctx.message.guild_id)
        reporter_member = await bot.rest.fetch_member(guild=guild.id, user=ctx.message.author.id)
        reported_member = await bot.rest.fetch_member(guild=guild.id, user=msg_ref.author.id)

        # ensure user info saved
        owner = await bot.rest.fetch_user(user=guild.owner_id)
        reporter_check = update_user_doc(ctx.message.author, reporter_member, guild, -1)
        reported_check = update_user_doc(msg_ref.author, reported_member, guild, 1)
        debug_msg = post_report_users_update(reporter_check, reported_check)

        if debug_msg:
            await owner.send(debug_msg)


# view status in server according to whistlebot
@bot.command()
async def member_status(ctx, *arg):
    """
    DMs user with full report of their activity on whistlebot.
    default without arg will prompt for user to type !status reporter or !status reports
    - reporter shows # reports/server, and # reports that resulted in an action
    - reports shows # times a user was reported/server, and # of each type of action taken against them/server
    """
    await ctx.message.author.send('WIP')


@bot.command()
async def report_update(ctx, *report_id):
    """
    DMs user with information about a particular report in the database.
    if no ID listed, prompts for a report_id
    if no ID found, displays error that no report was found (or that it may have been *deleted)
    * for now, although CRUD would prefer otherwise, for accountability reason only the repo owner
        can delete entries.

    if user matches reporter, lists server, user reported and if any actions were taken (if none, encourages to contact mods)
        - if action taken, lists action taken and by whom and thanks user

    if user matches reported, lists server,  reason for report and message that was reported.
        - if action taken, lists action taken but NOT by whom (to prevent retaliation)
        - encourages mediation with mods of server
    """

    await ctx.message.author.send('WIP')


# help function customized, time permitting

# run bot
bot.run()
