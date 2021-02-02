import os

from settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI, DISCORD_BOT_TOKEN, PERMISSIONS, \
    OAUTHLIB_INSECURE_TRANSPORT, SECRET_KEY

# UI interface
from quart import Quart, redirect, url_for
from quart_discord import DiscordOAuth2Session, requires_authorization

# set up app
app = Quart(__name__)

# env variables
app.secret_key = SECRET_KEY
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = OAUTHLIB_INSECURE_TRANSPORT
app.config["DISCORD_CLIENT_ID"] = DISCORD_CLIENT_ID
app.config["DISCORD_CLIENT_SECRET"] = DISCORD_CLIENT_SECRET
app.config["DISCORD_REDIRECT_URI"] = DISCORD_REDIRECT_URI  # add this to discord bot and edit env when deployed!
app.config["DISCORD_BOT_TOKEN"] = DISCORD_BOT_TOKEN

discord = DiscordOAuth2Session(app)

# attempt to start task
# this allows the bot to run alongside the server, but it cannot hear commands
# @app.before_serving
# async def startup():
#    loop = asyncio.get_event_loop()
#    app.discord_client = DiscordClient()
#    await app.discord_client.bot.login(DISCORD_BOT_TOKEN)
#    loop.create_task(app.discord_client.bot.connect())



# MODIFIED TEST CODE FROM QUART-DISCORD:
# Original code from https://github.com/jnawk/Quart-Discord/blob/master/tests/test_app.py
@app.route("/")
async def index():
    if not await discord.authorized:
        return f"""
        {HYPERLINK.format(url_for(".login"), "Login")} <br />
        {HYPERLINK.format(url_for(".invite_bot"), "Invite Bot with permissions 8")} <br />
        {HYPERLINK.format(url_for(".invite_oauth"), "Authorize with oauth and bot invite")}
        """

    return f"""
    {HYPERLINK.format(url_for(".me"), "@ME")}<br />
    {HYPERLINK.format(url_for(".logout"), "Logout")}<br />
    {HYPERLINK.format(url_for(".user_guilds"), "My Servers")}<br />
    {HYPERLINK.format(url_for(".invite_bot"), "Invite Bot with permissions 8")} <br /> 
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
    data = await discord.callback()
    redirect_to = data.get("redirect", "/")
    return redirect(redirect_to)

@app.route("/me/")
async def me():
    user = await discord.fetch_user()
    return f"""
<html>
<head>
<title>{user.name}</title>
</head>
<body><img src='{user.avatar_url or user.default_avatar_url}' />
<p>Is avatar animated: {str(user.is_avatar_animated)}</p>
<a href={url_for("my_connections")}>Connections</a>
<br />
</body>
</html>
"""


@app.route("/me/guilds/")
async def user_guilds():
    guilds = await discord.fetch_guilds()
    return "<br />".join([f"[ADMIN] {g.name}" if g.permissions.administrator else g.name for g in guilds])


# @app.route("/add_to/<int:guild_id>/")
# async def add_to_guild(guild_id):
#     user = await discord.fetch_user()
#     return await user.add_to_guild(guild_id)


# @app.route("/me/connections/")
# async def my_connections():
#     user = await discord.fetch_user()
#     connections = await discord.fetch_connections()
#     return f"""
# <html>
# <head>
# <title>{user.name}</title>
# </head>
# <body>
# {str([f"{connection.name} - {connection.type}" for connection in connections])}
# </body>
# </html>
# """


@app.route("/logout/")
async def logout():
    discord.revoke()
    return redirect(url_for(".index"))


@app.route("/secret/")
@requires_authorization
async def secret():
    return os.urandom(16)

HYPERLINK = '<a href="{}">{}</a>'

if __name__ == "__main__":
    app.run(debug=True)