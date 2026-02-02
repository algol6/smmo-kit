from discord import Bot,ApplicationContext, Forbidden, HTTPException,InvalidData, NotFound, Forbidden, Embed, Member, Color,AutocompleteContext,MISSING
from discord.abc import GuildChannel
from datetime import datetime, timezone, timedelta

from bot.discord_cmd.helpers.logger import logger
from bot.api.model._player_info import PlayerInfo
from bot.api import SMMOApi
from bot.database import Database
from bot.database.model import GuildStats

import requests
from io import BytesIO
from colorthief import ColorThief
from PIL import Image
from itertools import chain

def gen_is_empty(gen):
    try:
        first = next(gen)
    except StopIteration:
        return True,None
    except TypeError:
        return True,None
    return False,chain([first],gen)


async def get_current_season():
    # TODO: save season info into db
    res = tuple(await SMMOApi.get_guild_season())
    if datetime.fromisoformat(res[-1].starts_at[:-1]).timestamp() > datetime.now().timestamp():
        return res[-2]
    return res[-1]


async def get_current_season_id() -> int:
    # TODO: save season info into db
    res = tuple(await SMMOApi.get_guild_season())
    if datetime.fromisoformat(res[-1].starts_at[:-1]).timestamp() > datetime.now().timestamp():
        return res[-2].id
    return res[-1].id

async def get_war_guild(ctx:AutocompleteContext):
        guild_id = await Database.select_server(ctx.interaction.guild_id)
        global wars_list
        if 'wars_list' not in globals():
            wars_list = {} 
        if str(guild_id) not in wars_list or datetime.now().timestamp() - wars_list[str(guild_id)]["time"] >= 300:
            wars_list[str(guild_id)] = {"time":datetime.now().timestamp(),"wars":await SMMOApi.get_guild_wars(guild_id, 1),"autocomplete":[]}
            for war in wars_list[str(guild_id)]["wars"]:
                if war.guild_1["id"] == guild_id:
                    # guilds.append([war.guild_2["name"],war.guild_2["id"]])
                    wars_list[str(guild_id)]["autocomplete"].append([f"{war.guild_2["name"]} - {war.guild_2["id"]}",war.guild_1["kills"]])
                else:
                    if war.guild_2["id"] == guild_id:
                        # guilds.append([war.guild_1["name"],war.guild_1["kills"]])
                        wars_list[str(guild_id)]["autocomplete"].append([f"{war.guild_1["name"]} - {war.guild_1["id"]}",war.guild_2["kills"]])
            # wars_list[str(guild_id)]["autocomplete"] = sorted(wars_list[str(guild_id)]["autocomplete"],key=lambda item: item[1],reverse=True)
        try:
            return sorted([i[0] for i in wars_list[str(guild_id)]["autocomplete"] if ctx.value.lower() in i[0].lower()]) 
        except:
            return []

async def make_wars_emb(guild, c, v, s_lb, war_xp,bo:bool|None = None) -> str:
        xp: int = 0
        MAX_KILLS:int = 1500
        BASE_XP:int = 120000
        MULTIPLIER:float = 0.02

        if bo is None:
            xp = v.experience
            msg = f"**Total** XP of #{c+1} **[{guild.name}](https://simple-mmo.com/guilds/view/{guild.id})**: {xp:,}\n"
        elif bo:
            xp = s_lb[c-1].experience
            msg = f"**Total** XP of #{c} **[{guild.name}](https://simple-mmo.com/guilds/view/{guild.id})**: {xp:,}\n"
        else:
            xp = s_lb[c+1].experience
            msg = f"**Total** XP of #{c+2} **[{guild.name}](https://simple-mmo.com/guilds/view/{guild.id})**: {xp:,}\n"
        if guild.eligible_for_guild_war:
            # wars_ongoing = await SMMOApi.get_guild_wars(guild.id, 1)
            global wars_list
            if 'wars_list' not in globals():
                wars_list = {} 
            if str(guild.id) not in wars_list or datetime.now().timestamp() - wars_list[str(guild.id)]["time"] >= 300:
                wars_list[str(guild.id)] = {"time":datetime.now().timestamp(),"wars":await SMMOApi.get_guild_wars(guild.id, 1)}
            var: list[int] = [0,0,0,0,0,0,0]
            earnings: list[int] = [0,0,0,0,0,0]
            for w in wars_list[str(guild.id)]["wars"]:
                if w.guild_1["id"] == guild.id:
                    if w.guild_1["kills"] >= MAX_KILLS - 100:
                        var[0] += 1
                        if war_xp:
                            guild_2 = await SMMOApi.get_guild_info(w.guild_2["id"])
                            earnings[0] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_1["kills"]) * 50)
                    elif w.guild_1["kills"] >= MAX_KILLS - 200:
                        var[1] += 1
                        if war_xp:
                            guild_2 = await SMMOApi.get_guild_info(w.guild_2["id"])
                            earnings[1] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_1["kills"]) * 50)
                    elif w.guild_1["kills"] >= MAX_KILLS - 300:
                        var[2] += 1
                        if war_xp:
                            guild_2 = await SMMOApi.get_guild_info(w.guild_2["id"])
                            earnings[2] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_1["kills"]) * 50)
                    elif w.guild_1["kills"] >= MAX_KILLS - 400:
                        var[3] += 1
                        if war_xp:
                            guild_2 = await SMMOApi.get_guild_info(w.guild_2["id"])
                            earnings[3] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_1["kills"]) * 50)
                    elif w.guild_1["kills"] >= MAX_KILLS - 500:
                        var[4] += 1
                        if war_xp:
                            guild_2 = await SMMOApi.get_guild_info(w.guild_2["id"])
                            earnings[4] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_1["kills"]) * 50)
                    elif w.guild_1["kills"] >= MAX_KILLS - 600:
                        var[5] += 1
                        if war_xp:
                            guild_2 = await SMMOApi.get_guild_info(w.guild_2["id"])
                            earnings[5] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_1["kills"]) * 50)
                    else:
                        var[6] += 1
                else:
                    if w.guild_2["id"] == guild.id:
                        if w.guild_2["kills"] >= MAX_KILLS - 100:
                            var[0] += 1
                            if war_xp:
                                guild_2 = await SMMOApi.get_guild_info(w.guild_1["id"])
                                earnings[0] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_2["kills"]) * 50)
                        elif w.guild_2["kills"] >= MAX_KILLS - 200:
                            var[1] += 1
                            if war_xp:
                                guild_2 = await SMMOApi.get_guild_info(w.guild_1["id"])
                                earnings[1] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_2["kills"]) * 50)
                        elif w.guild_2["kills"] >= MAX_KILLS - 300:
                            var[2] += 1
                            if war_xp:
                                guild_2 = await SMMOApi.get_guild_info(w.guild_1["id"])
                                earnings[2] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_2["kills"]) * 50)
                        elif w.guild_2["kills"] >= MAX_KILLS - 400:
                            var[3] += 1
                            if war_xp:
                                guild_2 = await SMMOApi.get_guild_info(w.guild_1["id"])
                                earnings[3] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_2["kills"]) * 50)
                        elif w.guild_2["kills"] >= MAX_KILLS - 500:
                            var[4] += 1
                            if war_xp:
                                guild_2 = await SMMOApi.get_guild_info(w.guild_1["id"])
                                earnings[4] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_2["kills"]) * 50)
                        elif w.guild_2["kills"] >= MAX_KILLS - 600:
                            var[5] += 1
                            if war_xp:
                                guild_2 = await SMMOApi.get_guild_info(w.guild_1["id"])
                                earnings[5] += max(int(guild_2.current_season_exp * MULTIPLIER), BASE_XP) + ((MAX_KILLS - w.guild_2["kills"]) * 50)
                        else:
                            var[6] += 1
                
            if len(wars_list[str(guild.id)]) != 0:
                msg = (f"{msg}*War that is about to **win***:\n"
                        f"> War with more than **{MAX_KILLS-100}** kills: {var[0]} {f"(+ {format(earnings[0],",d")} gxp)" if war_xp else ""}\n"
                        f"> War with more than **{MAX_KILLS-200}** kills: {var[1]} {f"(+ {format(earnings[1],",d")} gxp)" if war_xp else ""}\n"
                        f"> War with more than **{MAX_KILLS-300}** kills: {var[2]} {f"(+ {format(earnings[2],",d")} gxp)" if war_xp else ""}\n"
                        f"> War with more than **{MAX_KILLS-400}** kills: {var[3]} {f"(+ {format(earnings[3],",d")} gxp)" if war_xp else ""}\n"
                        f"> War with more than **{MAX_KILLS-500}** kills: {var[4]} {f"(+ {format(earnings[4],",d")} gxp)" if war_xp else ""}\n"
                        f"> War with more than **{MAX_KILLS-600}** kills: {var[5]} {f"(+ {format(earnings[5],",d")} gxp)" if war_xp else ""}\n"
                        f"> *Other war*: {var[6]}\n"
                        )
        else:
            msg = f"{msg}> *They have no wars ongoing*\n"
        if bo is not None:
            msg = f"{msg}XP diff betweeen **{v.guild["name"]}-{guild.name}**: {format(xp - v.experience,",d")}\n"
        return msg
    

async def make_members_lb(data,current_date,task:bool=False):
        guild = await SMMOApi.get_guild_info(data.guild_id)
        if not guild:
            return None
        date = get_date_game(data.date)
        season = await get_current_season()
        guild_data = await Database.select_guild_stats(data.guild_id, date.year, date.month, date.day, season.id)

        x: int = guild_data.experience if guild_data else guild.current_season_exp
        total= [0, 0, 0, 0]
        var = []
        is_empty,guild_members = gen_is_empty(await SMMOApi.get_guild_members(data.guild_id))
        if is_empty:
            return None
        for m2 in guild_members:
            m1 = await Database.select_user_stat(m2.user_id,date.year,date.month,date.day)
            if m1 is not None:
                var.append(
                    {
                        "id": m1.smmo_id,
                        "levels": m2.level - m1.level,
                        "steps": m2.steps - m1.steps,
                        "npc_kills": m2.npc_kills - m1.npc_kills,
                        "user_kills": m2.user_kills - m1.user_kills,
                        "name": m2.name,
                    }
                )
                total[0] += m2.steps - m1.steps
                total[1] += m2.npc_kills - m1.npc_kills
                total[2] += m2.user_kills - m1.user_kills
                total[3] += m2.level - m1.level
        
        if len(var) == 0:
            return None
        emb = Embed(
            title=f"Members leaderboard",
            description=f"**Stats**: from <t:{int(current_date.timestamp())}> to <t:{int(current_date.timestamp() + 86400)}>\n"
            f"**Last update**: <t:{int(datetime.now().timestamp())}:R>\n"
            f"**Season**: {season.id}\n"
            f"**Season Ending**: <t:{int(datetime.fromisoformat(season.ends_at[:-1]).timestamp())}>\n"
            f"**Guild**: {guild.name}\n"
            f"**Exp**: {format(guild.current_season_exp, ',d')} (+{format(guild.current_season_exp - x, ',d')})",
            thumbnail=f"https://simple-mmo.com/img/icons/{guild.icon}",
        )

        emb.add_field(
            name=f"Steps: (Total: {format(total[0], ',d')})",
            value="\n".join(
                f"[{x['name']}](https://simple-mmo.com/user/view/{x['id']}): {format(x['steps'], ',d')}"
                for x in sorted(var, key=lambda member: (-member["steps"]))[:5]
            ),
            inline=False,
        )
        emb.add_field(
            name=f"NPC: (Total: {format(total[1], ',d')})",
            value="\n".join(
                f"[{x['name']}](https://simple-mmo.com/user/view/{x['id']}): {format(x['npc_kills'], ',d')}"
                for x in sorted(var, key=lambda member: (-member["npc_kills"]))[:5]
            ),
            inline=False,
        )
        emb.add_field(
            name=f"PVP: (Total: {format(total[2], ',d')})",
            value="\n".join(
                f"[{x['name']}](https://simple-mmo.com/user/view/{x['id']}): {format(x['user_kills'], ',d')}"
                for x in sorted(var, key=lambda member: (-member["user_kills"]))[:5]
            ),
            inline=False,
        )
        emb.add_field(
            name=f"Levels: (Total: {format(total[3], ',d')})",
            value="\n".join(
                f"[{x['name']}](https://simple-mmo.com/user/view/{x['id']}): {format(x['levels'], ',d')}"
                for x in sorted(var, key=lambda member: (-member["levels"]))[:5]
            ),
            inline=False,
        )
        if task:
            emb.set_footer(text="Updated every 10 min")
        return emb

async def make_gains_emb():
    season_id = await get_current_season_id()
    is_empty,season_lb = gen_is_empty(await SMMOApi.get_guild_season_leaderboard(season_id))
    if is_empty:
            return
    emb = Embed(
            title="Daily guild gains",
            description=f"**Stats**: from <t:{int((get_current_date_game()).timestamp())}>\n"
            f"**Last update**: <t:{int(datetime.now().timestamp())}:R>\n",
        )
    msg: str = ""
    title = ("Celestial", "Legendary", "Epic", "Elite", "Rare")
    date = get_current_date_game()
    for count in range(5):
        for _ in range(5):
            g = next(season_lb)
            s = await Database.select_guild_stats(g.guild["id"],date.year,date.month,date.day,season_id)
            if s is None:
                s = GuildStats(
                    date.year,
                    date.month,
                    date.day,
                    0,
                    g.guild["id"],
                    g.position,
                    g.experience,
                    season_id,
                )
            msg = f"{msg}#{g.position} **[{g.guild['name']}](https://simple-mmo.com/guilds/view/{g.guild['id']})**: {format(g.experience, ',d')} (+*{format(g.experience - s.experience, ',d')}*)xp"
            if g.position == s.position:
                msg = f"{msg}\n"
            elif g.position < s.position:
                msg = f"{msg} :arrow_up: +{s.position - g.position}\n"
            else:
                msg = f"{msg} :arrow_down: {s.position - g.position}\n"
        emb.add_field(name=title[count], value=msg, inline=False)
        msg = ""
    emb.set_footer(text="Updated every 10 min")
    return emb

async def get_channel_and_edit(client:Bot,channel_id:int,message_id:int=None,content=None,embed=None,view=None,delete_after=None):
    try:
        channel = await client.fetch_channel(channel_id)
        if not message_id:
            return await channel.send(content=content,embed=embed,delete_after=delete_after,view=view)
        message = await channel.fetch_message(message_id)
        await message.edit(content=content,embed=embed)
        if delete_after is not None:
            await Database.insert_delmsg(message.id,channel.id,delete_after)
        return message
    except NotFound:
        logger.warning("Channel Id Invalid")
        return False
    except Forbidden:
        logger.warning("Channel forbidden")
        return True
    except HTTPException:
        logger.warning("Failed to get the channel")
        return True
    except InvalidData:
        logger.warning("Unknown channel type was received from Discord")
        return True

async def send(ctx,content:str=None,embed:Embed=None,view=None,file=MISSING):
    try:
        if isinstance(ctx,ApplicationContext):
            return await ctx.followup.send(content=content,embed=embed,view=view,file=file)
        elif isinstance(ctx,GuildChannel):
            return await ctx.send(content=content,embed=embed,view=view,file=file)
    except Forbidden:
        logger.exception("Forbidden, i can't send messages there")
    except HTTPException:
        logger.exception("Internet fault not mine")
    except ValueError:
        logger.exception("Text in the embed too long")
    except NotFound:
        logger.exception("Not found: where i send the message?")

async def edit(ctx,content:str=None,embed:Embed=None)->None:
    try:
        if isinstance(ctx,ApplicationContext):
            await ctx.followup.edit(content=content,embed=embed)
        elif isinstance(ctx,GuildChannel):
            await ctx.edit(content=content,embed=embed)
    except Forbidden:
        logger.exception("Forbidden, i can't send messages there")
    except HTTPException:
        logger.exception("Internet fault not mine")
    except ValueError:
        logger.exception("Text in the embed too long")
    except NotFound:
        logger.exception("Not found: where i send the message?")
        

def get_date_game(tf:str) -> datetime:
    date = get_current_date_game()
    match tf:
        case "Past 7 Days":
            return date - timedelta(weeks=1)
        case "Yesterday":
            return date - timedelta(days=1)
        case "Daily":
            return date
        case "Monthly":
            return date - timedelta(weeks=4)
        case"In-Game Weekly":
            return date - timedelta(days=date.weekday())
        case "In-Game Monthly":
            return date.replace(day=28) if date.day > 28 or (date.day == 28 and date.hour >= 12) else (date - timedelta(weeks=4)).replace(day=28)
        case _:
            try:
                return datetime.strptime(tf,"%d/%m/%Y").replace(tzinfo=timezone.utc).replace(hour=12)
            except ValueError:
                logger.exception("when parsing data")

def get_current_date_game() -> datetime:
    da = datetime.now(tz=timezone.utc)
    temp_data = da.replace(hour=12, minute=0, second=0, microsecond=0)
    if da > temp_data:
        da = temp_data
    else:
        da = temp_data - timedelta(days=1)
    return da

async def get_user(ctx:ApplicationContext|None,smmo_id:int|None=None,user:Member|None=None) -> PlayerInfo | None:
    if ctx or user:
        u_id = user.id if user else ctx.user.id
        linked:bool = True
        bot_user = await Database.select_user_discord(u_id)
        if not bot_user:
            linked = False
            logger.info("User not linked")
        smmo_id = smmo_id if smmo_id else bot_user.smmo_id

    game_user = await SMMOApi.get_player_info(smmo_id)
    if not game_user or not linked:
        logger.warning("Wrong SMMO ID")
        await send(ctx,"Wrong smmo id or user not linked")
        return None
    return game_user


def get_dominant_color(image_url):
    response = requests.get(image_url)
    color_thief = ColorThief(BytesIO(response.content))
    dominant_color = color_thief.get_color(quality=1)
    return (dominant_color[0], dominant_color[1], dominant_color[2])


class Embed(Embed):
    def __init__(self,*,colour=None,color=None,title=None,type="rich",url=None,description=None,timestamp=None,fields=None,author=None,footer=None,image=None,thumbnail=None):
        color = (Color.from_rgb(*get_dominant_color(thumbnail)) if thumbnail else Color.random()) if not color else color
        # color = Color.random() if color is None else color
        super().__init__(colour=colour,color=color,title=title,type=type,url=url,description=description,timestamp=timestamp,fields=fields,author=author,footer=footer,image=image,thumbnail=thumbnail)
        self.set_footer(text="TEST MODE. Might get random error <-<")

def analyseImage(path):
    im = Image.open(path)
    results = {
        'size': im.size,
        'mode': 'full',
    }
    try:
        while True:
            if im.tile:
                tile = im.tile[0]
                update_region = tile[1]
                update_region_dimensions = update_region[2:]
                if update_region_dimensions != im.size:
                    results['mode'] = 'partial'
                    break
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    return results


def extract_and_resize_frames(path, resize_to=None):
    mode = analyseImage(path)['mode']
    im = Image.open(path)
    if not resize_to:
        resize_to = (im.size[0] // 2, im.size[1] // 2)
    i = 0
    p = im.getpalette()
    last_frame = im.convert('RGBA')
    all_frames = []

    try:
        while True:
            new_frame = Image.new('RGBA', im.size)
            if mode == 'partial':
                new_frame.paste(last_frame)

            new_frame.paste(im, (0, 0), im.convert('RGBA'))
            new_frame = new_frame.resize(resize_to,Image.NEAREST)
            all_frames.append(new_frame)

            i += 1
            last_frame = new_frame
            im.seek(im.tell() + 1)
    except EOFError:
        pass

    return all_frames

def resize_gif(path, save_as=None, resize_to=None):
        all_frames = extract_and_resize_frames(path, resize_to)

        if not save_as:
            save_as = path

        if len(all_frames) == 1:
            img = Image.open("./temp/ava1.gif")
            img = img.resize(resize_to,Image.NEAREST)

            img.save('./temp/ava2.gif')
        else:
            all_frames[0].save(save_as,optimize=True,save_all=True,append_images=all_frames[1:],loop=1000,quality=100,speed=0,disposal=2)

def human_format(x, pos):
    if x >= 1_000_000:
        return f'{x/1_000_000:.1f}M' if x % 1_000_000 else f'{int(x/1_000_000)}M'
    elif x >= 1_000:
        return f'{x/1_000:.1f}K' if x % 1_000 else f'{int(x/1_000)}K'
    else:
        return str(int(x))
    
def formattime(time: int) -> str:
        if time <= 0:
            return '0m'

        weeks, remaining_time = divmod(time, 60 * 24 * 7)
        days, remaining_time = divmod(remaining_time, 60 * 24)
        hours, minutes = divmod(remaining_time, 60)
        
        components = []
        if weeks: components.append(f"{weeks}w")
        if days: components.append(f"{days}d")
        if hours: components.append(f"{hours}h")
        if minutes: components.append(f"{minutes}m")
        
        return ''.join(components) or '0m'