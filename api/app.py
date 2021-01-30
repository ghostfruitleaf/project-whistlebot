import os

from settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI, DISCORD_BOT_TOKEN, DEBUG, OAUTHLIB_INSECURE_TRANSPORT, SECRET_KEY
from quart import Quart, redirect, url_for
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

app = Quart(__name__)

app.secret_key = SECRET_KEY
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = OAUTHLIB_INSECURE_TRANSPORT

app.config["DISCORD_CLIENT_ID"] = DISCORD_CLIENT_ID
app.config["DISCORD_CLIENT_SECRET"] = DISCORD_CLIENT_SECRET
app.config["DISCORD_REDIRECT_URI"] = DISCORD_REDIRECT_URI  # add this to discord bot and edit env when deployed!
app.config["DISCORD_BOT_TOKEN"] = DISCORD_BOT_TOKEN

discord = DiscordOAuth2Session(app)

HYPERLINK = '<a href="{}">{}</a>'

if __name__ == "__main__":
    app.run(debug=True) # change this when deploying

