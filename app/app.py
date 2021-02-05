import os
from datetime import datetime
import time

from settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI, DISCORD_BOT_TOKEN, PERMISSIONS, \
    OAUTHLIB_INSECURE_TRANSPORT, SECRET_KEY, MOTOR_URL

# UI interface
from quart import Quart, session, redirect, url_for
from database import Database
# from quart_motor import Motor
from quart_discord import DiscordOAuth2Session, requires_authorization

# in case the switch is happening
# import hikari

# set up app
app = Quart(__name__)

# env variables
app.secret_key = SECRET_KEY
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = OAUTHLIB_INSECURE_TRANSPORT
app.config["DISCORD_CLIENT_ID"] = DISCORD_CLIENT_ID
app.config["DISCORD_CLIENT_SECRET"] = DISCORD_CLIENT_SECRET
app.config["DISCORD_REDIRECT_URI"] = DISCORD_REDIRECT_URI  # add this to discord bot and edit env when deployed!
app.config["DISCORD_BOT_TOKEN"] = DISCORD_BOT_TOKEN

# database config
# app.config["MONGO_URI"] = MOTOR_URL
# mongo = Motor(app)
app_db = Database()

# set up discord API connection
discord = DiscordOAuth2Session(app)


# rest = hikari.RESTApp() # for when i can figure this out

# MOVE TO DB CLASS
def get_servers(user_id):
    """
    generates list of servers that can be monitored by user
    """
    servers = app_db.db.servers.find({})
    user_servers = []

    for server in servers:
        if int(user_id) in server['auth_users']: user_servers.append((server['server_id'], server['server_name']))

    return user_servers

def get_main_server(user_id):
    """
    Given a user, returns server_id of main server of user with profile in db
    """
    admin = app_db.db.admin_profiles.find_one({'admin_id': int(user_id)})
    return admin['main_server']


def ensure_admin_profile(user):
    """
    Given a user, creates a new profile for a user authorized to access the interface for a
    particular server.
    """
    if app_db.db.admin_profiles.find_one({'admin_id': int(user.id)}) is None:

        servers = get_servers(user.id)
        new_mod = {'admin_id': user.id,
                   'username': user.name,
                   'main_server': None if not servers else servers[0],
                   'auth_servers': servers
                   }

        app_db.db.admin_profiles.insert_one(new_mod)

# MODIFIED TEST CODE FROM QUART-DISCORD:
# Original code from https://github.com/jnawk/Quart-Discord/blob/master/tests/test_app.py

"""
FORMATTING (for now)
"""
def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset

def server_html(servers):
    server_objects = []

    for server in servers:
        string = f"""<li><b>{server[1]}</b> {HYPERLINK.format(url_for(".main", s_id=server[0]), "set as main server")}</li>"""
        server_objects.append(string)

    return server_objects

def report_html(reports):
    report_objects = []

    for report in reports:

        # get member info
        exhibit = app_db.db.exhibits.find_one({'reported_message_id': report['reported_message_id']})

        string = f"""<article>
                        <h2>report #{report['report_id']}</h3>
                        <h3>reported by user #{report['reporter_id']} on {datetime_from_utc_to_local(report['report_time'])}</h3>
                        <h4>user #{exhibit['reported_user_id']} wrote:</h4>
                        <p>"{exhibit['reported_message']}"</p>
                        <h5><b>on {datetime_from_utc_to_local(exhibit['reported_timestamp'])}</b></h5>
                     </article>"""
        report_objects.append(string)

    return "no reports here--all is well!" if not report_objects else " ".join(report_objects)


@app.route("/")
async def index():
    if not await discord.authorized:
        return f"""
         {HYPERLINK.format(url_for(".login"), "login")} <br />
         {HYPERLINK.format(url_for(".invite_oauth"), "login and add bot to server")}
         """

    # get user to check
    user = await discord.fetch_user()
    ensure_admin_profile(user)
    main_server = get_main_server(user.id)
    main_server_reports = list(app_db.db.reports.find({'server_id': int(main_server[0])}))

    print(main_server_reports)

    # WHERE DO I PUT THIS?
    session['servers'] = get_servers(user.id)
    session['main_server'] = main_server

    return f"""
    <html>
        <head>whistlebot mission control</head>
        <body>
            <header>
                <h1>welcome to whistlebot, {user.name}!</h1>
                <nav>
                    {HYPERLINK.format(url_for(".settings"), "settings")}<br />
                    {HYPERLINK.format(url_for(".logout"), "logout")}<br />
                    {HYPERLINK.format(url_for(".servers"), "servers")}<br />
                    {HYPERLINK.format(url_for(".reports"), "reports")}<br />
                    {HYPERLINK.format(url_for(".invite_bot"), "add whistlebot to new server")} <br />
                </nav>
            </header>
            <main>
                <h2><b>main server:</b> {get_main_server(user.id)[1]}</h2>
                <h2><b>today's reports</b></h2>
                <ul>{report_html(main_server_reports)}</ul>
            </main>
        </body>

    </html>
    """


@app.route("/login/")
async def login():
    return await discord.create_session()


# change to invite bot to any server
@app.route("/invite-bot/")
async def invite_bot():
    return await discord.create_session(
        scope=["bot"], permissions=PERMISSIONS, disable_guild_select=False
    )


@app.route("/invite-oauth/")
async def invite_oauth():
    return await discord.create_session(scope=["bot", "identify"], permissions=PERMISSIONS)


@app.route("/callback/")
async def callback():
    # prepare redirect
    data = await discord.callback()
    redirect_to = data.get("redirect", "/")
    return redirect(redirect_to)


@app.route("/settings/")
async def settings():
    user = await discord.fetch_user()
    return f"""
<html>
<head>
<title>{user.name}</title>
</head>
<body><img src='{user.avatar_url or user.default_avatar_url}' />
<p>Is avatar animated: {str(user.is_avatar_animated)}</p>
<br />
</body>
</html>
"""


@app.route("/servers")
async def servers():
    return "<br />".join(server_html(session['servers']))


@app.route("/main/<int:s_id>")
async def main(s_id):
    new_main = [v for i, v in enumerate(session['servers']) if v[0] == s_id]
    if not new_main:
        return f"""
                <h1>404: server not found</h1>
                {HYPERLINK.format(url_for(".servers"), "back to servers")}<br />
                """
    else:
        app_db.db.admin_profiles.update_one({'admin_id': discord.user_id}, {'$set': {'main_server': new_main[0]}})

    return redirect(url_for(".index"))


@app.route("/reports")
async def reports():
    main_server = session['main_server']
    main_server_reports = list(app_db.db.reports.find({'server_id': int(main_server[0])}))
    return f"""<ul>{" ".join(report_html(main_server_reports))}</ul>"""



@app.route("/logout/")
@requires_authorization
async def logout():
    discord.revoke()
    return redirect(url_for(".index"))


HYPERLINK = '<a href="{}">{}</a>'

if __name__ == "__main__":
    app.run(debug=True)
