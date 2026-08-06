from pydoc import text

from discord import (
    Guild,
    Intents,
    ActivityType,
    Activity,
    ApplicationContext,
    DiscordException,
    errors,
    SlashCommandGroup, SlashCommand,
    Forbidden
)
from os import getenv
from discord.channel import TextChannel
from pycord.multicog import Bot
from bot.database import Database, TrialDatabase
from bot.discord_cmd.helpers import helpers,command_utils,permissions
from bot.discord_cmd.helpers.logger import logger
from bot.api._api import ApiError

from requests import HTTPError
import re

from bot.discord_cmd.modules.admin._tasks import AdminTask

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
client.load_extension("bot.discord_cmd.modules.trial")


@command_utils.auto_defer()
@permissions.require_owner()
@command_utils.took_too_long()
async def test(ctx:ApplicationContext):

    await ctx.followup.send("NOTHING DONE !")

@client.event
async def on_application_command_error(ctx: ApplicationContext, error: DiscordException):
    guild = "No Guild. (Internal Error)"
    if ctx.guild:
        if hasattr(ctx.channel, "name"):
            guild = f"[{ctx.guild.name} #{ctx.channel.name}]"
        else:
            guild = f"[{ctx.guild.name} #{ctx.channel}]"
    logger.error("COMMAND [/%s] from %s:\n%s",ctx.command.qualified_name,guild,error)
    if isinstance(error.original, errors.NotFound):
        logger.warning("Error 'discord.errors.NotFound'")
        return await helpers.send(ctx,content="Error with discord, Try again.",delete_after=120)
    elif isinstance(error.original,ApiError):
        return await helpers.send(ctx,content="Error caused by: Api Limit Hit :/",delete_after=120)
    elif isinstance(error.original,HTTPError):
        return await helpers.send(ctx,content=f"Error caused by: {error}")
    print(error)
    await helpers.send(ctx,"Unexpected error. Try again later.",delete_after=120)

@client.event
async def on_ready():
    print("\nBOT READY")
    from bot.discord_cmd.modules.event._registration_view import RegistrationView
    from bot.discord_cmd.modules.trial._entry_view import EntryView
    client.add_view(RegistrationView())
    client.add_view(EntryView())
    server_setting = await TrialDatabase.select_trial_x_settings()
    print("Loading custom commands...")
    from bot.discord_cmd.modules.trial._trial import Trial
    try:
        await Trial.generate_trial_tree(client,server_setting)
    except errors.HTTPException:
        pass
    print("Loading custom commands DONE.")
    if not AdminTask.activity_check.is_running():
            AdminTask.activity_check.start()
    return
    print("Loading Tests")
    main_group = SlashCommandGroup(
                name="test",
                description="Test command",
                guild_ids=[1319980713541505044]
            )

    main_group.add_command(SlashCommand(
        func=test,
        name="test",
        description="test function",
        parent=main_group
    ))
    client.add_application_command(main_group)
    await client.sync_commands()
    print("Test loaded")

@client.event
async def on_member_update(before,after):
    if before.roles == after.roles:
        return
    new_roles = [role for role in after.roles if role not in before.roles]
    if not new_roles:
        return
    config = await Database.select_role_message_bulk([x.id for x in new_roles])
    if not config:
        return
    for role in new_roles:
        if role.id not in config:
            continue
        links = config[role.id].text.split("links:")
        if links is None or len(links) in (0,1):
            view = None
        else:
            links = re.findall(r'\[(.*?)\]', links[1])
            view = helpers.LinksUrlButton(links)
        try:
            ch = await client.fetch_channel(config[role.id].channel_id)
            msg = await ch.send(
                content=after.mention,
                embed=helpers.get_emb_role_message(config[role.id],after.mention,role.name),
                view=view
            )
            await msg.edit(content="")
        except Forbidden:
            continue

@client.event
async def on_guild_join(guild:Guild):
    channel:TextChannel|None = guild.system_channel

    if not channel:
        first = True
        for text_channel in guild.text_channels:
            if text_channel.permissions_for(guild.me).send_messages:
                if first:
                    first = False
                    continue
                channel = text_channel
                break

    if channel:
        logger.info("Bot joined guild: %s",channel.name)
        emb = helpers.Embed(
            title="Hello, I'm SMMO-Kit!",
            description="Thanks for adding me to your server!"
        )
        emb.add_field(
            name="Getting Started",
            value=(
                "Type `/user verify` to verify your account!\n"
                "Then you can link the server to a guild with `/admin link server`"
            )
        )
        emb.set_footer(text="Developed by Algol")

        await channel.send(embed=emb)

@client.event
async def on_member_join(member):
    conf = await Database.select_join_roles(member.guild.id)
    if conf is None:
        return
    channel = None
    if conf.msg != "":
        try:
            channel = client.get_channel(conf.channel)
            if isinstance(channel, TextChannel):
                msg = await channel.send(content=conf.msg,delete_after=500)
        except:
            pass
    player = await helpers.get_user(user=member)
    if player is None:
        try:
            if channel is None:
                channel = client.get_channel(conf.channel)
            if isinstance(channel, TextChannel):
                msg = await channel.send(content="> To automatically get roles link with the bot using '/user verify' and following the instructions or ask to the moderators.",delete_after=120)
        except:
            pass
        return
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
