from discord import ApplicationContext
from functools import wraps
from time import time
from bot.database import Database

def auto_defer(ephemeral:bool=True):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                ctx:ApplicationContext = args[1]
                await ctx.defer(ephemeral=ephemeral)
            return await func(*args, **kwargs)
        return wrapped
    return wrapper

def took_too_long() -> bool:
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                ctx:ApplicationContext = args[1]
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
            if len(args) >= 2 and isinstance(args[1], ApplicationContext):
                t = time()
                f = await func(*args, **kwargs)
                await Database.insert_statistics(fun,time()-t)
            return f 
        return wrapped
    return wrapper