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
client.load_extension("bot.discord_cmd.modules.event")
client.load_extension("bot.discord_cmd.modules.utility")
client.load_extension("bot.discord_cmd.modules.worldboss")
client.load_extension("bot.discord_cmd.modules.extra")
client.load_extension("bot.discord_cmd.modules.community")
#client.load_extension("bot.discord_cmd.modules.trial")


@client.event
async def on_application_command_error(ctx: ApplicationContext, error: DiscordException):
    guild = "No Guild. (Internal Error)"
    if ctx.guild:
        try:
            guild = f"[{ctx.guild.name} #{ctx.channel.name}]"
        except:
            guild = f"[{ctx.guild.name} #{ctx.channel}]"

    logger.error("COMMAND [/%s] from %s:\n%s",ctx.command.qualified_name,guild,error)
    if isinstance(error, errors.NotFound):
        logger.warning("Error 'discord.errors.NotFound'")
        return await helpers.send(ctx,content=f"Error with discord, Try again.")
    elif isinstance(error,ApiError):
        return await helpers.send(ctx,content=f"Error caused by: {error}")
    elif isinstance(error,HTTPError):
        return await helpers.send(ctx,content=f"Error caused by: {error}")
    await helpers.send(ctx,"Unexpected error. Try again later.",delete_after=3600)

@client.event
async def on_ready():
    from bot.discord_cmd.modules.event._registration_view import RegistrationView
    client.add_view(RegistrationView())

@client.event
async def on_member_join(member):
    conf = await Database.select_join_roles(member.guild.id)
    if conf is None:
        return
    if conf.msg != "":
        try:
            channel = await client.get_channel(conf.channel)
            msg = await channel.send(content=conf.msg,delete_after=500)
        except:
            pass
    player = await helpers.get_user(user=member)
    if player is None:
        try:
            msg = await channel.send(content="> To automatically get roles link with the bot using '/user verify' and following the instructions or ask to the moderators.",delete_after=500)
            return
        except:
            pass
    guild_id = await Database.select_server(member.guild.id)
    if guild_id == player.guild.id:
        await helpers.give_join_roles(member,conf.groles)
    else:
        await helpers.give_join_roles(member,conf.vroles)
    
def main():
    try:
        logger.info("Starting Bot. Goodmorning!")
        client.run(getenv("DISCORD_TOKEN"))
    except KeyboardInterrupt:
        logger.info("CTRL+C ded xd.")
    except Exception as e:
        logger.exception("Error on client.main() in _client.py:\n%s",str(e))
    finally:
        logger.info("Exting Bot. Goodbye!")


