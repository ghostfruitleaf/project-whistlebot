"""
DB_FUNCTIONS.PY

Contains function relevant to maintaining database entries.
"""
import settings
from pymongo import MongoClient

"""
DOC GENERATION FUNCTIONS
"""

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
        'reported_edits': [] if reported_message.edited_timestamp is None else [(reported_message.edited_timestamp,
                                                                                 reported_message.content)],
        # array of edited messages as detected by bot on checks
        'deleted': False,  # confirms if message is deleted
        'times_reported': 1,
        'reports': [int(report_id)]  # reports made about message
    }

    return exhibit


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

class Database:
    """
    DATABASE CLASS

    holds database management methods
    """
    def __init__(self):
        self.status = ('active', 'kicked', 'left', 'banned')
        self.client = MongoClient(settings.CONNECTION_URL)
        self.db = self.client['whistlebot-db']

    """
    DATABASE CREATE/ENSURE METHODS

    creates new objects in whistlebot database.
    """

    def add_server(self, guild):
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
                                       guild.system_channel_id if guild.system_channel_id is not None else 0,
                                   # channel for user agreement
                                   'user_agrmt_message_id': None,  # message to check for agreement
                                   'settings_roles': [],  # roles that can change server settings
                                   'settings_users': [],  # roles that can change server users
                                   'alert_roles': [],  # roles to be alerted of report
                                   'alert_users': [],  # users to be alerted of report
                                   'alert_channel_id': None  # id of channel to receive reports, if specified
                                   }
                      }

        return True if self.db.servers.insert_one(server_doc).acknowledged else False

    def save_reported_message(self, reported_message, report_id, reporter_id):
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
        find_exhibit = self.db.exhibits.find_one(query)
        # reported message exists; object is returned
        if find_exhibit is not None:

            # check to see if repeat reporter
            reporter_exists = False
            reports = find_exhibit['reports']

            for id_num in reports:
                if self.db.reports.find_one({'report_id': id_num, 'reporter_id': reporter_id}):
                    reporter_exists = True
                    break

            # don't update unless it's a new reporter
            if not reporter_exists:
                # new values
                rpt_times = find_exhibit['times_reported'] + 1
                reports = reports.append(int(report_id))
                update_val = {'$set': {'times_reported': rpt_times, 'reports': reports}}
                return True if self.db.exhibits.update_one({'reported_message_id': int(reported_message.id)}, update_val).modified_count == 1 else False

            # flag to tell reporter not re-report a message, please -- this should help prevent spam
            else:
                return True, 0
            return True, 1

        # add to db
        else:
            return (True, 1) if self.db.exhibits.insert_one(exhibit).acknowledged else (False, 0)

    def create_report(self, report, reported_message):
        """
        create_report(report,reported_message)

        - creates report document in database using a message starting with !flag command
          and message that is replied to
        - triggered through authorized !flag command call from a user in a server
        - triggers creation of server document in database if not already existing
        - triggers creation of users if not already in database AFTER creation of report.
        """
        rptd_msg = self.save_reported_message(reported_message, report.id, report.author.id)  # get tuple code

        # no message saved successfully
        if rptd_msg[0] and rptd_msg[1] < 1:
            return None
        # message saved
        elif rptd_msg[0]:
            # generate report
            report_content = report.content.replace('!flag', '', 1)

            # find flags
            flags = []
            server_flags = self.db.servers.find_one({'server_id': int(report.guild_id)})

            for word in server_flags:
                if word in report_content.lower(): flags.append(word)

            # ALWAYS generate report if saved
            new_report = generate_report(report, report_content, flags, reported_message)

            if not self.db.reports.insert_one(new_report).acknowledged: return False
            # check that server is in database
            # check that both users are in database (needs finally)
            return True
        else:
            # indicates attempt to double report a message
            return False

    def ensure_member_profile(self, user, member, guild, report_status=0):
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
        find_member = self.db.member_profiles.find_one(query)

        # create new member profile
        if find_member is None:
            new_member = generate_member_profile(user, member, guild, report_status)

            # first ensure profile is added
            if not self.db.member_profiles.insert_one(new_member).acknowledged: return False

            # since user exists, we need to update the user object with a query to the new profile
            get_user = self.db.discordusers.find_one({'discord_id': int(user.id)})
            get_user['profiles'].append(query)

            update_user = self.db.discordusers.update_one({'discord_id': int(user.id)}, {"$set": {'profiles': get_user['profiles']}})

            return True if update_user.modified_count == 1 else False

        else:  # profile exists
            if report_status == 0: return True  # do nothing if this was not initiated by a report

            # update with new report counts
            update_dict = {}
            if report_status == 1:
                update_dict = {'reports_received': find_member['reports_received'] + 1}
            elif report_status < 0:
                update_dict = {'reports_sent': find_member['reports_sent'] + 1}

            if report_status != 0:
                return True if self.db.member_profiles.update_one(query, {"$set": update_dict}).modified_count == 1 else False

    def update_user_doc(self, user, member, guild, report_status=0):
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
        get_user = self.db.discordusers.find_one({'discord_id': user.id})
        user_exists = False
        # create new user profile
        if get_user is None:
            new_user = {'discord_id': user.id,
                        'profiles': [{'server_id': guild.id, 'user_id': user.id}],  # add query just for guild the
                        # request came from for now
                        'deleted': False,  # we have other ways to confirm this info
                        'alts': []  # eventually there will be logic added to identify alts for accts
                        }
            added_user = self.db.discordusers.insert_one(new_user)

            if added_user.acknowledged:
                user_exists = True
        else:
            user_exists = True

        # update/create member
        profile_exists = True if self.ensure_member_profile(user, member, guild, report_status) else False

        return user_exists, profile_exists  # tuple code for updates
