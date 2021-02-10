import os
from datetime import datetime
import time

from settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI, DISCORD_BOT_TOKEN, PERMISSIONS, \
    OAUTHLIB_INSECURE_TRANSPORT, SECRET_KEY, MOTOR_URL

# UI interface
from quart import Quart, session, redirect, url_for, render_template, flash
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

# MODIFIED TEST CODE FROM QUART-DISCORD:
# Original code from https://github.com/jnawk/Quart-Discord/blob/master/tests/test_app.py

"""
FORMATTING (for now)
"""

def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset

def report_html(reports):
    report_objects = []

    for report in reports:

        # get member info
        exhibit = app_db.db.exhibits.find_one({'reported_message_id': report['reported_message_id']})
        reporter = app_db.db.discordusers.find_one({'discord_id': report['reporter_id']})
        reported = app_db.db.discordusers.find_one({'discord_id': exhibit['reported_user_id']})

        report_hash = {'report_id': report['report_id'],
                       'reporter_id': report['reporter_id'],
                       'reporter_name': reporter['discord_name'] + '#' + reporter['discriminator'],
                       'report_time': datetime_from_utc_to_local(report['report_time']),
                       'reported_name': reported['discord_name'] + '#' + reported['discriminator'],
                       'reported_user_id': exhibit['reported_user_id'],
                       'reported_message': exhibit['reported_message'],
                        'reported_timestamp': datetime_from_utc_to_local(exhibit['reported_timestamp'])
                        }
        report_objects.append(report_hash)

    return "no reports here--all is well!" if not report_objects else report_objects


@app.route("/")
async def index():
    if not await discord.authorized:
        return f"""
         {HYPERLINK.format(url_for(".login"), "login")} <br />
         {HYPERLINK.format(url_for(".invite_oauth"), "login and add bot to server")}
         """

    # get user to check
    user = await discord.fetch_user()
    app_db.ensure_admin_profile(user)
    main_server = app_db.get_main_server(user.id)
    main_server_reports = list(app_db.db.reports.find({'server_id': int(main_server[0])}))

    navlinks =HYPERLINK.format(url_for(".logout"), "logout") + HYPERLINK.format(url_for(".invite_bot"), "add whistlebot to new server")

    # WHERE DO I PUT THIS?
    session['servers'] = app_db.get_servers(user.id)
    session['main_server'] = main_server
    session['main_server_reports'] = report_html(main_server_reports)
    return await render_template('index.html',
                                 reports=session['main_server_reports'],
                                 main_server=main_server,
                                 servers=session['servers'],
                                 user=user,
                                 nav=NAV_AUTH)


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
    await flash('logged in!')
    return redirect(redirect_to)


@app.route("/reports/")
@requires_authorization
async def reports():
    return f"""<h1>{session['main_server_reports']}</h1>"""


@app.route("/settings/")
@requires_authorization
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


@app.route("/main/<int:s_id>")
async def main(s_id):
    new_main = [v for i, v in enumerate(session['servers']) if v[0] == s_id]
    if not new_main:
        return f"""
                <h1>404: server not found</h1>
                {HYPERLINK.format(url_for(".index"), "back to home")}<br />
                """
    else:
        app_db.db.admin_profiles.update_one({'admin_id': discord.user_id}, {'$set': {'main_server': new_main[0]}})

    return redirect(url_for(".index"))


@app.route("/ban/<int:s_id>/<int:u_id>")
@requires_authorization
async def ban(s_id, u_id):
    print('BAN')


@app.route("/kick/<int:s_id>/<int:u_id>")
@requires_authorization
async def kick(s_id, u_id):
    print('KICK')


@app.route("/warn/<int:u_id>")
@requires_authorization
async def warn(u_id):
    print('WARN')


@app.route("/ignore/<int:r_id>")
@requires_authorization
async def ignore(r_id):
    print("IGNORE")


@app.route("/logout/")
@requires_authorization
async def logout():
    discord.revoke()
    return redirect(url_for(".index"))


HYPERLINK = '<a href="{}">{}</a>'

NAV_AUTH = {'settings': 'settings', 'logout': 'logout', 'invite-bot': 'invite whistlebot to a new server'}
NAV = {'login': 'login', 'invite-oauth': 'login and add bot to server'}

if __name__ == "__main__":
    app.run(debug=True)
