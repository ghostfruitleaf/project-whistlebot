"""
BOT.PY (@PaulineChane on GitHub)

command discord bot for project-whistlebot to create reports and track authorized interactions
with whistlebot on discord. primarily creates new entries for users, servers, and reports in database.
"""
import settings
import hikari
import lightbulb
from database import Database, post_report_users_update
from datetime import datetime, timezone

# start db
bot_db = Database()

"""
DISCORD BOT/METHODS

ensures all users, reports, servers documented in database. 
may need to optimize as an ensure function? 
"""

# initialize bot
intents = (hikari.Intents.ALL_GUILDS | hikari.Intents.ALL_MESSAGES)

bot = lightbulb.Bot(token=settings.DISCORD_BOT_TOKEN,
                    prefix='!',
                    insensitive_commands=True, intents=intents)

"""

EVENT LISTENERS

"""

"""
UPDATING SERVER INFO
"""

@bot.listen(hikari.GuildLeaveEvent)
async def clear_server_settings(event):
    """
    for now, simple deletes server profile, which for security reasons will be refreshed
    if server re-adds whistlebot.

    currently reports pertaining to server are archived, may change to a mass delete.
    """
    bot_db.db.servers.delete_one({'server_id': int(event.guild_id)})


@bot.listen(hikari.GuildAvailableEvent)
async def check_server_profile(event):
    """
    Checks that servers that whistlebot is in has profiles in database.
    Creates new profile if one not currently found, or once whistlebot joins database.
    """
    # check if server is in db
    find_server = bot_db.db.servers.find_one({'server_id': int(event.guild.id)})

    # get owner object in case message needed to send alert
    get_id = event.guild.owner_id
    owner = await bot.rest.fetch_user(user=get_id)

    # add new server profile to db
    if find_server is None:
        add_new_server = bot_db.add_server(event.guild)

        # sends warning message that server profile was not added to system.
        if not add_new_server: await owner.send('whistlebot was unable to create a new profile for the following '
                                                f'server: {event.guild.name}. please try re-adding the bot or'
                                                'adding an issue at https://github.com/PaulineChane/project-whistlebot.')


"""
MESSAGE UPDATES
"""


@bot.listen(hikari.GuildMessageUpdateEvent)
async def check_exhibit_update(event):
    """
    Checks for attempt to edit a message that was reported.
    """
    # check first if message was reported
    query = {'reported_message_id': int(event.message.id)}
    edited_message = bot_db.db.exhibits.find_one(query)

    # if found, update entry with edits
    if edited_message is not None:
        edited_message['reported_edits'].append((event.message.edited_timestamp, event.message.content))
        bot_db.db.exhibits.update_one(query, {'$set': {'reported_edits': edited_message['reported_edits']}})

        # send message to author if too many edit attempts
        if len(edited_message['reported_edits']) > 3:
            await event.message.author.send('**whistlebot update:**\n'
                                            'it has been brought to our attention that you have attempted to edit'
                                            f'message {event.message.id} multiple times. please note that the'
                                            'edits have been saved and will be viewable by server admins.')


@bot.listen(hikari.GuildMessageDeleteEvent)
async def check_exhibit_delete(event):
    """
    Checks for attempt to delete a reported message.
    """
    deleted_messages = []

    # in event of bulk delete, check for multiple reported messages
    for message_id in event.message_ids:
        query = {'reported_message_id': int(message_id)}
        get_msg = bot_db.db.exhibits.find_one(query)

        # message was reported!
        if get_msg is not None:
            # update db to indicated deleted message
            bot_db.db.exhibits.update_one(query, {"$set": {'deleted': True}})
            # add to array of deleted messages
            deleted_messages.append(str(message_id))

    if deleted_messages:
        # get author from db
        first_msg = bot_db.db.exhibits.find_one({'reported_message_id': int(deleted_messages[0])})
        author = await bot.rest.fetch_user(user=int(first_msg['reported_user_id']))

        # gen string of message ids
        str_ids = ', '.join(deleted_messages)

        # send message to author
        await author.send('**whistlebot update:**\n'
                          'it has been brought to our attention that you have attempted to delete\n'
                          f'messages: **{str_ids}**, currently reported to our database.\n'
                          'this action will be viewable by server admins.')


"""
MEMBER UPDATES
"""

@bot.listen(hikari.MemberCreateEvent)
async def find_returning_member(event):
    """
    tracks members with reports/who have reported returning to server
    """
    query = {'server_id': int(event.guild_id), 'user_id': int(event.user.id)}
    get_member_profile = bot_db.db.member_profiles.find_one(query)

    # user is a rejoin, refresh roles and make note
    if get_member_profile is not None:
        new_data = {'$set': {'server_status': 'active',
                             'role_ids': event.member.role_ids,
                             'notes': get_member_profile['notes'] + f' NOTE: rejoined {event.member.joined_at}'}}
        bot_db.db.member_profiles.update_one(query, new_data)


@bot.listen(hikari.MemberDeleteEvent)
async def mark_member_left(event):
    """
    maintains server profile of member in db, but marks as left
    """
    # check if member is in database
    query = {'server_id': int(event.guild_id), 'user_id': int(event.user.id)}
    get_member_profile = bot_db.db.member_profiles.find_one(query)

    if get_member_profile is not None:
        status = 'left' if get_member_profile['server_status'] == 'active' else get_member_profile['server_status']
        new_data = {'$set': {'server_status': status, 'notes': get_member_profile['notes'] +
                                                               f' NOTE: {status} {datetime.now(timezone.utc)}'}}
        bot_db.db.member_profiles.update_one(query, new_data)


@bot.listen(hikari.MemberUpdateEvent)
async def update_member_info(event):
    """
    checks if member is in db. if so, adds nickname if nickname changes, refreshes role_id list
    """

    # check if member is in database
    query = {'server_id': int(event.guild_id), 'user_id': int(event.member.user.id)}
    get_member_profile = bot_db.db.member_profiles.find_one(query)

    if get_member_profile is not None:
        if get_member_profile['nicknames'] and (get_member_profile['nicknames'][-1] != str(event.member.nickname)):
            get_member_profile['nicknames'].append(str(event.member.nickname))  # add nickname if changed

        new_data = {'$set': {'nicknames': get_member_profile['nicknames'],
                             'roles': event.member.role_ids}}  # refresh roles

        bot_db.db.member_profiles.update_one(query, new_data)


"""

COMMANDS

"""


# flags a message by replying
@lightbulb.guild_only()
@bot.command()
async def flag(ctx):
    """
    Reply to a server message with !flag in order to report it.
    Please note server moderation staff may require extra steps before you can use this function.
    """
    msg_type = str(ctx.message.type)  # ensure the message is a reply
    # default message: DM error if no reply found
    msg = '**no report sent!** please reply to a server message you wish to flag!'

    # handle various reply cases
    if msg_type == 'REPLY':

        # get reported message
        msg_ref = ctx.message.referenced_message

        # get guild/owner info
        guild = await bot.rest.fetch_guild(guild=ctx.message.guild_id)
        owner = await bot.rest.fetch_user(user=guild.owner_id)

        # authorization check
        member_profile = bot_db.db.member_profiles.find_one({'server_id': int(ctx.message.guild_id),
                                                            'user_id': int(ctx.message.author.id)})

        can_flag = member_profile['user_argmt_status']


        if (not can_flag) and (can_flag is not None):
             msg = 'your ability to use the report feature has been revoked.\nplease contact mods if you believe this was in error.'

        # don't report the bot
        elif msg_ref.author.id == int(settings.DISCORD_CLIENT_ID):  # do we need to check for an attempt to report a bot?
            msg = 'do not attempt to report whistlebot. no report has been sent.'

        # attempting to report a server owner
        elif msg_ref.author.id == owner.id:
            msg = 'reporting server owners is unfortunately outside of whistlebot capabilities due to discord limitations.\n'
            msg += 'if this is a serious issue that cannot be resolved with the moderators,\n'
            msg += 'we recommend reporting the owner per discord\'s instructions below:\n'
            msg += 'https://support.discord.com/hc/en-us/articles/360000291932-How-to-Properly-Report-Issues-to-Trust-Safety'
            msg += '\n no report has been sent.'
        # trying to self-report or report a system user.
        elif ctx.message.author.id == msg_ref.author.id:
            msg = 'please do not attempt to use whistlebot functionality to spam. no report has been sent.'

        else:
            # below should only trigger if report is created
            rpt_success = bot_db.create_report(ctx.message, msg_ref)

            if rpt_success is None:
                msg = 'we have already received your previous report on this message.'
            elif not rpt_success:
                msg = 'we were not able to create a report. please try again.'
            else:
                await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
                msg = 'thank you for your report -- it is currently under review by the admin team.'
                msg += f"\nif you wish to see status updates of your report, please type **!report_update {ctx.message.id}.** "

        # send msg
        await ctx.message.author.send("**whistlebot update!**\n" + msg)

        if msg_ref.author.id != int(settings.DISCORD_CLIENT_ID):
            # get guild
            reporter_member = await bot.rest.fetch_member(guild=guild.id, user=ctx.message.author.id)
            reported_member = await bot.rest.fetch_member(guild=guild.id, user=msg_ref.author.id)

            # ensure user info saved
            reporter_check = bot_db.update_user_doc(ctx.message.author, reporter_member, guild, -1)
            reported_check = bot_db.update_user_doc(msg_ref.author, reported_member, guild, 1)
            debug_msg = post_report_users_update(reporter_check, reported_check)

            if debug_msg:
                await owner.send(debug_msg)


# view status in server according to whistlebot
# @bot.command()
# async def member_status(ctx, mode=None):
#     """
#     DMs user with full report of their activity on whistlebot.
#     """
#     """
#     default without arg will prompt for user to type !status reporter or !status reports
#     - reporter shows # reports/server, and # reports that resulted in an action
#     - reports shows # times a user was reported/server, and # of each type of action taken against them/server
#     """
#     await ctx.message.author.send('this is a work in progress for a potential second sprint.')


@bot.command()
async def report_update(ctx, report_id=0):
    """
    DMs user with information about a particular report in the database.
    """

    """
    if no ID listed, prompts for a report_id
    if no ID found, displays error that no report was found (or that it may have been *deleted)
    * for now, although CRUD would prefer otherwise, for accountability reason only the repo owner
        can delete entries.

    if user matches reporter, lists server, user reported and if any actions were taken (if none, encourages to
    contact mods) - if action taken, lists action taken and by whom and thanks user

    if user matches reported, lists server,  reason for report and message that was reported.
        - if action taken, lists action taken but NOT by whom (to prevent retaliation)
        - encourages mediation with mods of server
    """
    report = bot_db.db.reports.find_one({'report_id': int(report_id)})
    msg = ''
    if report is None:
        msg = 'please enter a valid report id.'
    elif report['reporter_id'] == int(ctx.message.author.id):
        action = report['action']

        guild = await bot.rest.fetch_guild(guild=report['server_id'])
        if not action['auth_user_id']:
            msg = f'no action has been taken yet.\nplease contact mods at server **{guild.name}**ß if you think this is an urgent issue.'
        else:
            # user = await bot.rest.fetch_user(user=action['auth_user_id'])
            action_taken = action['action_taken']
            time = str(action['timestamp'])
            auth_user = action['auth_user_id']
            msg = f'<@{auth_user}> performed the following:\n**{action_taken}**\non {time} UTC based on your report.'
            msg += f'\nif you disagree with this decision, please discuss this with the moderation team at server: \n**{guild.name}**'
    await ctx.message.author.send('**whistlebot update!**\n' + msg)


# help function customized, time permitting

# run bot
bot.run()
