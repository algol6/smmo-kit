from discord import (
    Intents,
    ActivityType,
    Activity,
    ApplicationContext,
    DiscordException,
    errors
)
from os import getenv
from pycord.multicog import Bot
from bot.database import Database
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.api._api import ApiError
from asyncio import run

from requests import HTTPError

intent = Intents.default()
intent.members = True
client = Bot(intents=intent, activity=Activity(name="SimpleMMO", type=ActivityType.watching))

client.load_extension("bot.discord_cmd.modules.command_groups")
client.load_extension("bot.discord_cmd.modules.admin")
client.load_extension("bot.discord_cmd.modules.guild")
client.load_extension("bot.discord_cmd.modules.user")
client.load_extension("bot.discord_cmd.modules.orphanage")
client.load_extension("bot.discord_cmd.modules.diamond")
#client.load_extension("bot.discord_cmd.modules.event")
client.load_extension("bot.discord_cmd.modules.utility")
client.load_extension("bot.discord_cmd.modules.worldboss")
client.load_extension("bot.discord_cmd.modules.extra")


@client.event
async def on_application_command_error(ctx: ApplicationContext, error: DiscordException):
    guild = "No Guild. (Internal Error)"
    if ctx.guild:
        try:
            guild = f"[{ctx.guild.name} #{ctx.channel.name}]"
        except:
            guild = f"[{ctx.guild.name} #{ctx.channel}]"

    logger.error(" from %s:\n%s",guild,error)
    if isinstance(error, errors.NotFound):
        logger.warning("Error 'discord.errors.NotFound'")
    elif isinstance(error,ApiError):
        return await helpers.send(ctx,content=f"Error caused by: {error}")
    elif isinstance(error,HTTPError):
        return await helpers.send(ctx,content=f"Error caused by: {error}")
    await helpers.send(ctx,"Unexpected error. Try again later.")

def main():
    try:
        #run(Database.create_table())
        logger.info("Starting Bot. Goodmorning!")
        client.run(getenv("DISCORD_TOKEN"))
    except KeyboardInterrupt:
        logger.info("CTRL+C ded xd.")
    except Exception as e:
        logger.exception("Error on client.main() in _client.py:\n%s",str(e))
    finally:
        logger.info("Exting Bot. Goodbye!")


