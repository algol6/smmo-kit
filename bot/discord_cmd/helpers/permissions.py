import functools

from discord import ApplicationContext, Member
from bot.discord_cmd.helpers.logger import logger
from bot.api import SMMOApi
from bot.database import Database
from time import time

async def is_admin_or_staff(ctx: ApplicationContext) -> bool:
    if isinstance(ctx.author, Member): 
        if ctx.author.guild_permissions.administrator:
            return True,None
        if ctx.author.guild_permissions.manage_channels:
            return True,None
        if ctx.author.guild_permissions.manage_guild:
            return True,None
        if ctx.author.guild_permissions.manage_roles:
            return True,None
    roles_id = set(y.id for y in ctx.user.roles)
    for x in await Database.select_staff(await Database.select_server(ctx.guild_id)):
        if x.role_id in roles_id:
            return True,None
    user = await Database.select_user_discord(ctx.user.id)
    if user is not None and user.smmo_id is not None:
        profile = await SMMOApi.get_player_info(user.smmo_id)
        if profile is not None and profile.guild.id is not None and await Database.select_server(ctx.guild_id) == profile.guild.id:
            guild_members = await SMMOApi.get_guild_members(profile.guild.id)
            return any(x.user_id == user.smmo_id and x.position != "Member" for x in guild_members),profile
    return False,None

async def is_owner(ctx: ApplicationContext) -> bool:
    return ctx.user.id == 652879730063966209

def require_admin_or_staff():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                ctx: ApplicationContext = args[1]
                is_staff,user = await is_admin_or_staff(ctx)
                if not (is_staff or await is_owner(ctx)):
                    logger.info("User [%s] is not admin in: %s",ctx.user.name,ctx.guild.name)
                    await ctx.respond(
                        content="You do not have permission to run this command or you or the server aren't linked with the bot.",
                        ephemeral=True
                    )
                    return
                # TODO: fix where user is None cases
                ctx.user_game_profile = user
            return await func(*args, **kwargs)
        return wrapped
    return wrapper


def require_owner():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                ctx: ApplicationContext = args[1]
                if not await is_owner(ctx):
                    logger.info("%s is not Owner",ctx.user.name)
                    await ctx.respond(
                        content="You do not have permission to run this command. Ask Algol.",
                        ephemeral=True
                    )
                    return
                
            return await func(*args, **kwargs)
        return wrapped
    return wrapper


async def is_linked_account(ctx: ApplicationContext) -> bool:
    user = await Database.select_user_discord(ctx.user.id)
    return user is not None and user.smmo_id is not None,user

def require_linked_account():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                ctx: ApplicationContext = args[1]
                is_linked,discord_user=await is_linked_account(ctx)
                if not is_linked:
                    await ctx.respond(
                        content="You need to be linked. use `/user verify` to link your account.",
                        ephemeral=True
                    )
                    return
                
                ctx.discord_user = discord_user
            return await func(*args, **kwargs)
        return wrapped
    return wrapper


def require_linked_server():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                ctx: ApplicationContext = args[1]
                guild_id = await Database.select_server(ctx.guild_id)
                if not guild_id:
                    await ctx.respond(
                        content="""
                        ```Server need to be linked.\n
                        Use `/admin link server` adding the Guild ID of the guild you want to link.\n
                        You can find the Guild ID in the link (ex: `https://simple-mmo.com/guilds/view/ID_HERE`)\n
                        To Link the server you need to be Staff of the guild or have the perms to manage the server/channel/roles.```
                        """,
                        ephemeral=True
                    )
                    return
                ctx.user_guild_id = guild_id
            return await func(*args, **kwargs)
        return wrapped
    return wrapper


