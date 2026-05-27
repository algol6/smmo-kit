from discord import ApplicationContext
from functools import wraps
from time import time
from bot.api import SMMOApi
from bot.database import Database, TrialDatabase

def auto_defer(ephemeral:bool=True):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            ctx = next((arg for arg in args if isinstance(arg, ApplicationContext)), None)
            if ctx:
                await ctx.defer(ephemeral=ephemeral)
            return await func(*args, **kwargs)
        return wrapped
    return wrapper

def took_too_long() -> bool:
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            ctx = next((arg for arg in args if isinstance(arg, ApplicationContext)), None)
            if ctx:
                t = time()
                f = await func(*args, **kwargs)
                if time() - t > 10:
                    await ctx.followup.send(
                            content=f"<@{ctx.author.id}> Command loaded.",
                            ephemeral=True
                        )
            return f
        return wrapped
    return wrapper

def statistics(fun:str="") -> bool:
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            #ctx = next((arg for arg in args if isinstance(arg, ApplicationContext)), None)
            #if ctx:
            #    t = time()
            #    f = await func(*args, **kwargs)
            #    await Database.insert_statistics(f"/{ctx.command.qualified_name}",time()-t)
            #    return f
            #return await func(*args, **kwargs)
            t = time()
            f = await func(*args, **kwargs)
            await Database.insert_statistics(fun,time()-t)
            return f
        return wrapped
    return wrapper

def trial_enabled() -> bool:
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            ctx = next((arg for arg in args if isinstance(arg, ApplicationContext)), None)
            if ctx:
                trial = await TrialDatabase.select_trial_by_server_id(ctx.guild_id)
                if not trial:
                    await ctx.respond(
                        content="```This server has no quest system enable.\nUse '/admin create_quest_system' to create one.```",
                        ephemeral=True
                    )
                    return
                ctx.trial = trial
            return await func(*args, **kwargs)
        return wrapped
    return wrapper

def trial_user() -> bool:
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            ctx = next((arg for arg in args if isinstance(arg, ApplicationContext)), None)
            if ctx:
                trial = await TrialDatabase.select_trial_by_server_id(ctx.guild_id)
                if not trial:
                    await ctx.respond(
                        content="```This server has no System enabled.```",
                        ephemeral=True
                    )
                    return
                if not trial.enabled:
                    await ctx.respond(
                        content="```System temporarily disabled.```",
                        ephemeral=True
                    )
                    return
                user = await Database.select_user_discord(ctx.user.id)
                ig_user = await SMMOApi.get_player_info(user.smmo_id)
                if ig_user is None:
                    await ctx.respond(
                        content="```Error. Try again later```",
                        ephemeral=True
                    )
                    return
                if trial.guild_id != ig_user.guild.id:
                    await ctx.respond(
                        content="```You need to be member of the guild to use the system.```",
                        ephemeral=True
                    )
                    return
                ctx.trial = trial
                ctx.ig_user = ig_user
            return await func(*args, **kwargs)
        return wrapped
    return wrapper