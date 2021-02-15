from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID") # client id from from discord developer portal
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")  # client secret from discord developer portal
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")  # callback for discord oauth - be sure to allow this address at discord developer portal!
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # bot token secret
DEBUG = os.getenv("DEBUG")  # for debug mode
OAUTHLIB_INSECURE_TRANSPORT = os.getenv("OAUTHLIB_INSECURE_TRANSPORT")
SECRET_KEY = os.getenv("SECRET_KEY")  # for quart app
PERMISSIONS = int(os.getenv("PERMISSIONS"))  # permissions for bot
CONNECTION_URL = os.getenv("CONNECTION_URL")  # database connection URL
PREFIX = os.getenv("PREFIX")  # command prefix for bot commands ex) ! for !command