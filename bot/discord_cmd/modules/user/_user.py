from discord import Bot,ApplicationContext,slash_command,guild_only,option,Member,File
from discord.ext.commands import Cog
from pycord.multicog import subcommand
from urllib.request import urlretrieve
from PIL.Image import open
from datetime import time, datetime, timezone, timedelta
from random import choice
from string import ascii_lowercase, ascii_uppercase, digits
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.dates import DateFormatter
from pandas import set_option

from bot.api import SMMOApi
from bot.database import Database
from bot.discord_cmd.helpers import command_utils, permissions, helpers
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.modules.user._equipment_view import EquipmentView
from bot.discord_cmd.modules.user._unverify_button import UnverifyButton
from bot.discord_cmd.modules.user._leaderboard_view import LeaderboardView
from bot.discord_cmd.modules.user._tasks import UsersTask

from PIL import Image
from io import BytesIO
from requests import get
class Users(Cog):
    def __init__(self, client):
        self.client = client

    @subcommand("user")
    @slash_command(description="Show the user avatar")
    @guild_only()
    @option(name="size",choices=[1,2,3,4,5,10])
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user avatar")
    @command_utils.took_too_long()
    async def avatar(self,ctx:ApplicationContext,user:Member=None,smmo_id:int=None,size:int=3):
        game_user = await helpers.get_user(ctx, smmo_id, user)

        emb = helpers.Embed(title=f"{game_user.name}'s Avatar")
        if size == 1:
            emb.set_image(url=f"https://simple-mmo.com{game_user.avatar}")
            return await helpers.send(ctx,embed=emb)
        
        response = get(f"https://simple-mmo.com{game_user.avatar}")
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))
        img.save("./temp/ava1.gif")
        #urlretrieve(f"https://simple-mmo.com{game_user.avatar}","./temp/ava1.gif")
        #img = open("./temp/ava1.gif")
        helpers.resize_gif("./temp/ava1.gif","./temp/ava2.gif",(int(img.size[0]*size), int(img.size[1]*size)))
        file = File("./temp/ava2.gif", filename="ava3.gif")
        emb.set_image(url="attachment://ava3.gif")
        return await helpers.send(ctx,file=file, embed=emb)
    
    @subcommand("user")
    @slash_command(description="Show the best user stats registered by the bot")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user lb")
    @command_utils.took_too_long()
    async def lb(self,ctx:ApplicationContext):
        user = ctx.discord_user
        view = LeaderboardView()
        view.data = [
            tuple(await Database.select_all_best("STEPS")),
            tuple(await Database.select_all_best("NPC")),
            tuple(await Database.select_all_best("PVP")),
            tuple(await Database.select_all_best("LEVEL")),
        ]
        view.user_id = user.smmo_id
        await view.send(ctx)

    @subcommand("user", independent=True)
    @slash_command(description="Get the graph if your stats.")
    @guild_only()
    @option(name="from_date", description="Write data in format dd/mm/yyyy")
    @option(name="to_date", description="Write data in format dd/mm/yyyy")
    @option(name="level", description="Show level line")
    @option(name="steps", description="Show steps line")
    @option(name="npc", description="Show npc kills line")
    @option(name="pvp", description="Show pvp kills line")
    @option(name="subplots", description="Divide it into different graphs")
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user graph")
    @command_utils.took_too_long()
    async def graph(self,ctx:ApplicationContext,user:Member=None,smmo_id:int=None,from_date:str=None,to_date:str=None,gains:bool=False,level:bool=True,steps:bool=True,npc:bool=True,pvp:bool=True,subplots:bool=True):
        if not any((level, steps, npc, pvp)):
            return await helpers.send(ctx,content="Select at least one among 'level','steps','npc' or 'pvp'")
        try:
            s_date = datetime.strptime(from_date, "%d/%m/%Y") if from_date is not None else None
            e_date = datetime.strptime(to_date, "%d/%m/%Y") if to_date is not None else None
        except:
            return await helpers.send(ctx,content="Wrong date format. use dd/mm/yyyy format")

        game_user = await helpers.get_user(ctx, smmo_id, user)
        
        y: list[str] = []
        legen: list[str] = []
        if level:
            y.append("level")
            legen.append("Levels")
        if steps:
            y.append("steps")
            legen.append("Steps")
        if npc:
            y.append("npc_kills")
            legen.append("NPC Kills")
        if pvp:
            y.append("user_kills")
            legen.append("PVP Kills")
        all_stats = await Database.select_all_user_stats(game_user.id)
        if s_date is not None:
            all_stats = all_stats[all_stats["date"] >= s_date]
        if e_date is not None:
            all_stats = all_stats[all_stats["date"] <= e_date]
        if len(all_stats) == 0:
            return await helpers.send(ctx,content="No data found")
        if gains:
            all_stats['daily_npc'] = all_stats['npc_kills'].diff()
            all_stats['daily_steps'] = all_stats['steps'].diff()
            all_stats['daily_user_kills'] = all_stats['user_kills'].diff()
            all_stats['daily_level'] = all_stats['level'].diff()

            all_stats['daily_npc'] = all_stats['daily_npc'].fillna(0)
            all_stats['daily_steps'] = all_stats['daily_steps'].fillna(0)
            all_stats['daily_user_kills'] = all_stats['daily_user_kills'].fillna(0)
            all_stats['daily_level'] = all_stats['daily_level'].fillna(0)
            for i,x in enumerate(y):
                if x == "level":
                    y[i] = "daily_level"
                elif x == "steps":
                    y[i] = "daily_steps"
                elif x == "npc_kills":
                    y[i] = "daily_npc"
                elif x == "user_kills":
                    y[i] = "daily_user_kills"

        set_option("styler.format.thousands", ",")
        set_option('display.float_format', lambda x: f'{x:,.0f}')
        plt.style.use("dark_background")
        axes = all_stats.plot(
            y=y,
            x="date",
            subplots=subplots,
            title=f"{game_user.name}'s{' Gains' if gains else ''} graph",
            xlabel="Date",
            label = legen
        )
        date_formatter = DateFormatter('%d-%b-%Y') 
        if subplots:
            for ax in axes:
                ax.yaxis.set_major_formatter(FuncFormatter(helpers.human_format))
                ax.xaxis.set_major_formatter(date_formatter)
        else:
            axes.yaxis.set_major_formatter(FuncFormatter(helpers.human_format))
            axes.xaxis.set_major_formatter(date_formatter)

        plt.tight_layout()
        plt.savefig("./temp/graph.png")
        plt.close()
        file = File("./temp/graph.png", filename="graph.png")
        emb = helpers.Embed(
            title=f"{game_user.name}'s{' Gains' if gains else ''} graph",
            description=f"From <t:{int(all_stats['time'].min())}> to <t:{int(all_stats['time'].max())}>",
        )
        emb.set_image(url="attachment://graph.png")
        return await helpers.send(ctx,file=file,embed=emb)
    
    @subcommand("user", independent=True)
    @slash_command(description="Get the average stats.")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user avg")
    @command_utils.took_too_long()
    async def avg(self,ctx:ApplicationContext,user:Member = None, smmo_id: int = None):
        game_user = await helpers.get_user(ctx, smmo_id, user)
        if not game_user:
            return
        avg = await Database.select_avg_stats(game_user.id)
        avgw = await Database.select_avg_stats_week(game_user.id)
        day_count = await Database.select_counter_user_stats(game_user.id)
        avg_msg = f"Could not retrive data."
        avgw_msg = f"Could not retrive data."
        TEMPLATE:str = "Levels: {lvl:,.0f}\nSteps: {stp:,.0f}\nNPC Kills: {npc:,.0f}\nPVP Kills: {pvp:,.0f}"
        if avg and avg.level:
            avg_msg = TEMPLATE.format(lvl=avg.level,stp=avg.steps,npc=avg.npc_kills,pvp=avg.user_kills)
        if avgw and avgw.level:
            avgw_msg = TEMPLATE.format(lvl=avgw.level,stp=avgw.steps,npc=avgw.npc_kills,pvp=avgw.user_kills)
        
        emb = helpers.Embed(
            title=f"[{game_user.id}] {game_user.name} Average Stats",
            url=f"https://simple-mmo.com/user/view/{game_user.id}",
            thumbnail=f"https://simple-mmo.com{game_user.avatar}",
            description=f"Last updated: <t:{round(datetime.now().timestamp())}:R>",
        )
        emb.add_field(
            name=f"All-Time Average gains ({day_count:,} days):",
            value=avg_msg,
            inline=False,
        )

        emb.add_field(
            name="Past 7 Days Average gains:",
            value=avgw_msg,
            inline=False,
        )
        emb.set_footer(text="Data limited to that saved in the Database.")
        await helpers.send(ctx,embed=emb)
        
    @subcommand("user", independent=True)
    @slash_command(description="Get the overall stats.")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user overall")
    @command_utils.took_too_long()
    async def overall(self,ctx:ApplicationContext,user:Member = None, smmo_id: int = None):
        game_user = await helpers.get_user(ctx, smmo_id, user)
        if not game_user:
            return
        best = await Database.select_best(game_user.id)
        is_empty,best = helpers.gen_is_empty(best)
        if is_empty:
            return await helpers.send(ctx,content="No stats found, wait for server reset")
        emb = helpers.Embed(
            title=f"[{game_user.id}] {game_user.name}",
            url=f"https://simple-mmo.com/user/view/{game_user.id}",
            thumbnail=f"https://simple-mmo.com{game_user.avatar}",
            description=f"Last updated: <t:{round(datetime.now().timestamp())}:R>",
        )
        for x in best:
            title = ""
            if x.category == "STEPS":
                ind = 3
                title = "Most Steps done in a day:"
            elif x.category == "NPC":
                ind = 4
                title = "Most NPC killed in a day:"
            elif x.category == "PVP":
                ind = 5
                title = "Most User killed in a day:"
            elif x.category == "LEVEL":
                ind = 2
                title = "Most Level gains in a day:"
            emb.insert_field_at(
                index=ind,
                name=title,
                value=f"Timeframe: <t:{int(x.date) - 86400}> - <t:{int(x.date)}>\nLevels: {int(x.levels):,}\nSteps: {int(x.steps):,}\nNPC Kills: {int(x.npc):,}\nPVP Kills: {int(x.pvp):,}",
                inline=False,
            )
        emb.set_footer(text="Data limited to that saved in the Database.")
        await helpers.send(ctx,embed=emb)

    @subcommand("user", independent=True)
    @slash_command(description="Add a profile to track the stats WILL NOT be linked with your discord!")
    @guild_only()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user verify2")
    @command_utils.took_too_long()
    async def verify2(self, ctx: ApplicationContext, smmo_id: int):
        profile = await SMMOApi.get_player_info(smmo_id)
        if profile is None:
            return await helpers.send(ctx,"Profile not found")
        await Database.insert_track(smmo_id)
        await helpers.send(ctx,content=f"User '{profile.name}' Added.")

    @subcommand("user", independent=True)
    @slash_command(description="Get the stats from a custom timeframe")
    @guild_only()
    @option(name="from_date", description="Write data in format dd/mm/yyyy")
    @option(name="to_date", description="Write data in format dd/mm/yyyy")
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user advstats")
    @command_utils.took_too_long()
    async def advstats(self,ctx:ApplicationContext,from_date:str,to_date:str,user:Member=None,smmo_id:int=None):
        try:
            s_date = datetime.strptime(from_date, "%d/%m/%Y")
            e_date = datetime.strptime(to_date, "%d/%m/%Y")
        except:
            return await helpers.send(ctx,content="Wrong date format. use dd/mm/yyyy format")

        if s_date >= e_date:
            return await helpers.send(ctx,content="Starting date can't be after than ending date")
        game_user = await helpers.get_user(ctx, smmo_id, user)
        if game_user is None:
            return
        stats1 = await Database.select_user_stat(game_user.id,s_date.year,s_date.month,s_date.day)
        if stats1 is None:
            return await helpers.send(ctx,"No data found for the starting date")
        stats2 = await Database.select_user_stat(game_user.id,e_date.year,e_date.month,e_date.day)
        if stats2 is None:
            return await helpers.send(ctx,"No data found for the ending date")

        emb = helpers.Embed(
            title=f"[{game_user.id}] {game_user.name}",
            url=f"https://simple-mmo.com/user/view/{game_user.id}",
            thumbnail=f"https://simple-mmo.com{game_user.avatar}",
            description=f"Stats: <t:{int(stats1.time)}> to <t:{int(stats2.time)}>\n")
        emb.add_field(
            name="Levels:",
            value=f"{(stats2.level - stats1.level) if stats2.level - stats1.level >= 0 else stats2.level:,}",
            inline=True)
        emb.add_field(
            name="Steps:", value=f"{stats2.steps - stats1.steps:,}", inline=True
        )
        emb.add_field(
            name="NPC Kills:",
            value=f"{stats2.npc_kills - stats1.npc_kills:,}",
            inline=True)
        emb.add_field(
            name="Player Kills:",
            value=f"{stats2.user_kills - stats1.user_kills:,}",
            inline=True)
        await helpers.send(ctx,embed=emb)

    @subcommand("user")
    @slash_command(description="Show the user equipment")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user equipment")
    @command_utils.took_too_long()
    async def equipment(self,ctx:ApplicationContext,user:Member=None,smmo_id:int=None):
        smmo_id = (await Database.select_user_discord(user.id) if user else ctx.discord_user).smmo_id if not smmo_id else smmo_id
        is_empty,equip = helpers.gen_is_empty(await SMMOApi.get_player_equipment(smmo_id))
        if is_empty:
            return await helpers.send(ctx,content="The user doesn't have equipped item")
        equipment_view = EquipmentView()
        equipment_view.data = tuple(equip)
        equipment_view.user = await SMMOApi.get_player_info(smmo_id)
        await equipment_view.send(ctx)

    @subcommand("user")
    @slash_command(description="Link your discord account with your smmo account")
    @guild_only()
    @command_utils.auto_defer()
    @command_utils.statistics("/user verify")
    @command_utils.took_too_long()
    async def verify(self, ctx: ApplicationContext, smmo_id:int=None):
        x1 = await Database.select_user_discord(ctx.user.id)
        x3 = await Database.select_user_smmoid(smmo_id)
        if x3 is not None:
            await helpers.send(ctx,content="Looks like this SMMO ID is already linked with another discord account, if you keep going the old account will be unlinked.")
        message1 = (
            "## To verify you account follow these steps:\n"
            "- Copy this code `{}`.\n"
            "- [Change your in game motto](https://simple-mmo.com/changemotto/) to the code above.\n"
            "- Copy your 'User ID', you can find at the bottom of your profile's stats page (*it looks like this*: `User ID: XXXXXX`) or in the link of your profile `https://simple-mmo.com/user/view/XXXXXX`\n"
            "- Use again this command adding your User ID `/user verify XXXXXX`"
        )
        if x1 is None:
            verification_code = "".join(choice(ascii_uppercase + ascii_lowercase + digits) for _ in range(15))
            await helpers.send(ctx,message1.format(verification_code))
            return await Database.insert_user(ctx.user.id, verification_code)
        if x1.smmo_id is not None:
            return await helpers.send(ctx,content="Your account is already linked")
        if smmo_id is None:
            return await helpers.send(ctx,"Insert your SMMO ID as parameter in the command.")

        x2 = await SMMOApi.get_player_info(smmo_id)
        if x2 is not None and x1.verification == x2.motto.strip():
            logger.info(f"User registered ({smmo_id}): {x2.name} lvl:{x2.level} {f'Guild: {x2.guild.name}' if x2.guild else 'No Guild'}")
            if x3 is not None:
                await Database.delete_user(x3.discord_id)
            if not await Database.update_user(ctx.user.id, smmo_id):
                return await helpers.send(ctx,content="Unknow Error.")
            await helpers.send(ctx,content="Your account is linked.\nYou can set back your motto.")
            return
        await helpers.send(ctx,content=message1.format(x1.verification))

    @subcommand("user")
    @slash_command(description="Unlink your discord with your smmo profile")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer()
    @command_utils.statistics("/user unverify")
    @command_utils.took_too_long()
    async def unverify(self,ctx:ApplicationContext):
        unverify_view = UnverifyButton()
        unverify_view.user_id = ctx.user.id
        await unverify_view.send(ctx)

    @subcommand("user")
    @slash_command(description="Show linked smmo profile")
    @guild_only()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user profile")
    @command_utils.took_too_long()
    async def profile(self,ctx:ApplicationContext,user:Member=None,smmo_id:int=None):
        profile = await helpers.get_user(ctx, smmo_id, user)
        if profile is None:
            return
        emb = helpers.Embed(
            title=profile.name,
            url=f"https://simple-mmo.com/user/view/{profile.id}",
            thumbnail=f"https://simple-mmo.com{profile.avatar}",
            description=f"ID: {profile.id}\n"
            f"Last seen: <t:{profile.last_activity}:R>\n"
            f"Attackable: {'Never' if profile.safeMode else 'Now' if profile.hp > (profile.max_hp / 2) else 'Later'}\n",
        )

        emb.add_field(name="Level:", value=f"{profile.level:,}", inline=True)
        emb.add_field(name="Gold:", value=f"{profile.gold:,} :coin:", inline=True)
        emb.add_field(
            name="Health:",
            value=f"{profile.hp:,}/{profile.max_hp:,} :heart:",
            inline=True)
        emb.add_field(
            name="Strength:",
            value=f"{profile.strength:,} :crossed_swords:",
            inline=True)
        emb.add_field(
            name="Defence:",
            value=f"{profile.defence:,} :shield:",
            inline=True)
        emb.add_field(
            name="Dexterity:",
            value=f"{profile.dexterity:,} :boot:",
            inline=True)
        if profile.guild.name is not None:
            emb.add_field(
                name="Guild:",
                value=f"[{profile.guild.name}](https://simple-mmo.com/guilds/view/{profile.guild.id})",
                inline=True)
        emb.add_field(
            name="Safe mode:",
            value=':white_check_mark:' if profile.safeMode else ':x:',
            inline=True)
        emb.add_field(
            name="Current location:",
            value=profile.current_location.name,
            inline=True)
        await helpers.send(ctx,embed=emb)

    @subcommand("user", independent=True)
    @slash_command(description="Get the daily/weekly/monthly stats")
    @guild_only()
    @option(name="timeframe",choices=["Daily","Past 7 Days","In-Game Weekly","Yesterday","Monthly","In-Game Monthly"])
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/user stats")
    @command_utils.took_too_long()
    async def stats(self,ctx:ApplicationContext,user:Member=None,smmo_id:int=None,timeframe:str="Daily"):
        date = helpers.get_date_game(timeframe)
        to_date = helpers.get_current_date_game() 
        if timeframe != "Yesterday":
            to_date += timedelta(days=1)
        current_stats = await helpers.get_user(ctx, smmo_id, user)
        if not current_stats:
            return
        stats = await Database.select_user_stat(current_stats.id, date.year, date.month, date.day)
        if stats is None:
            return await helpers.send(ctx,"No data, may take up to 24h to load")
        quests: bool = False
        bounties: bool = False
        if stats.quest_performed != -1 and current_stats.quests_performed != -1:
            quests = True
        if stats.bounties_completed != -1 and current_stats.bounties_completed != -1:
            bounties = True
        emb = helpers.Embed(
            title=f"[{current_stats.id}] {current_stats.name}",
            url=f"https://simple-mmo.com/user/view/{current_stats.id}",
            description=f"Stats: <t:{int(stats.time)}> to <t:{int(to_date.timestamp())}>\n"
            f"Last updated: <t:{int(datetime.now().timestamp())}:R>",
            thumbnail=f"https://simple-mmo.com{current_stats.avatar}",
        )
        emb.add_field(
            name="Levels:",
            value=f"{(current_stats.level - stats.level) if current_stats.level - stats.level >= 0 else current_stats.level:,}",
            inline=True,
        )
        emb.add_field(
            name="Steps:", value=f"{current_stats.steps - stats.steps:,}", inline=True
        )
        emb.add_field(
            name="NPC Kills:",
            value=f"{current_stats.npc_kills - stats.npc_kills:,}",
            inline=True,
        )
        emb.add_field(
            name="Player Kills:",
            value=f"{current_stats.user_kills - stats.user_kills:,}",
            inline=True,
        )
        if quests:
            emb.add_field(
                name="Quests:",
                value=f"{current_stats.quests_performed - stats.quest_performed:,}",
                inline=True,
            )
        if bounties:
            emb.add_field(
                name="Bounties:",
                value=f"{current_stats.bounties_completed - stats.bounties_completed:,}",
                inline=True,
            )
        await helpers.send(ctx,embed=emb)


def setup(client:Bot):
    client.add_cog(Users(client))
    client.add_cog(UsersTask(client))
