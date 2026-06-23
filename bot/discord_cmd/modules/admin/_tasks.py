from asyncio import sleep
from datetime import datetime, time, timedelta, timezone
from random import choice

from discord import Bot
from discord.errors import Forbidden, HTTPException, NotFound
from discord.ext.commands import Cog
from discord.ext.tasks import loop

from bot.api import ApiError, SMMOApi
from bot.core._guild_members import GuildMembersManager
from bot.database import Database
from bot.discord_cmd.helpers import command_utils, helpers, permissions
from bot.discord_cmd.helpers.logger import logger
from bot.database.model import CompleteLb, GainsLeaderboard


class AdminTask(Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.check_montly_reward.start()
        self.set_new_gain_lb.start()
        self.update_gains_lb.start()
        self.create_new_daily_leaderboard.start()
        self.update_leaderboards.start()
        self.activity_check.start()
        self.cleanup_msg.start()
        self.update_season.start()

        self.set_up_new_lb.start()
        self.update_lb.start()
        # self.eff.start()
        # import asyncio
        # asyncio.run(self.eff())

    def cog_unload(self) -> None:
        self.check_montly_reward.cancel()
        self.set_new_gain_lb.cancel()
        self.update_gains_lb.cancel()
        self.create_new_daily_leaderboard.cancel()
        self.update_leaderboards.cancel()
        self.activity_check.cancel()
        self.cleanup_msg.cancel()
        self.update_season.cancel()

        self.set_up_new_lb.cancel()
        self.update_lb.cancel()

    @loop(time=time(hour=11, minute=59))
    async def set_up_new_lb(self):
        await self.update_complete_lb(False)
        await self.create_new_complete_leaderboard()

    @loop(minutes=10)
    async def update_lb(self):
        await self.update_complete_lb()

    async def generic_update_lbs(self, fetch_data, make_emb, skip: bool = True):
        dt = datetime.now(tz=timezone.utc)
        if skip and dt.hour == 12 and dt.minute <= 30:
            return
        data = await fetch_data()
        emb = None
        for d in data:
            timestamp = int(helpers.get_date_game(d.timeframe).timestamp())
            if skip and timestamp != d.timestamp:
                continue
            if isinstance(d,CompleteLb):
                emb = await make_emb(d.guild_id, d.category, timestamp)
            elif emb is None and isinstance(d,GainsLeaderboard):
                emb = await make_emb()

            emb = await make_emb(d.guild_id, timestamp)
            if not emb:
                logger.warning("Could not make the embed for the guild %s", d.guild_id)
                continue
            if not await helpers.get_channel_and_edit(self.client, d.channel_id, d.message_id, embed=emb):
                logger.info("lb error: channel not found: %s", d.channel_id)

    async def generic_create_lbs(self, fetch_data, delete_data, update_data, skip: bool = True):
        await sleep(120)  # to have the date to the next day for helpers.get_current_date_game()
        data = await fetch_data()
        for d in data:
            timestamp = int(helpers.get_date_game(d.timeframe).timestamp())
            if d.timestamp == timestamp:
                continue
            try:
                channel = await self.client.fetch_channel(d.channel_id)
                emb = helpers.Embed(title="Loading leaderboard...")
                message = await channel.send(embed=emb)
                await update_data(channel.id, timestamp, d.message_id, message.id)
            except NotFound:
                logger.info("Channel not found (create_new_complete_leaderboard)")
                logger.info("Removing a lb cause: channel not found: %s", d.channel_id)
                await delete_data(d.channel_id)
                continue
            except Forbidden:
                logger.info("Removing a lb cause: channel forbidden: %s", d.channel_id)
                await delete_data(d.channel_id)
                continue
            except HTTPException:
                logger.warning("Internet fault")
                continue

    async def create_new_complete_leaderboard(self):
        await sleep(
            120
        )  # to have the date to the next day for helpers.get_current_date_game()
        data = await Database.select_all_cmp_lb()
        for d in data:
            timestamp = int(helpers.get_date_game(d.timeframe).timestamp())
            if d.timestamp == timestamp:
                continue
            try:
                channel = await self.client.fetch_channel(d.channel_id)
                emb = helpers.Embed(title="Loading leaderboard...")
                message = await channel.send(embed=emb)
                await Database.update_cmp_lb(
                    channel.id, timestamp, d.message_id, message.id
                )
            except NotFound:
                logger.info("Channel not found (create_new_complete_leaderboard)")
                logger.info(
                    "Removing a gains lb cause: channel not found: %s", d.channel_id
                )
                await Database.delete_cmp_lb(d.channel_id)
                continue
            except Forbidden:
                logger.info(
                    "Removing a gains lb cause: channel forbidden: %s", d.channel_id
                )
                await Database.delete_cmp_lb(d.channel_id)
                continue
            except HTTPException:
                logger.warning("Internet fault")
                continue

    async def update_complete_lb(self, skip: bool = True):
        #await self.generic_update_lbs(Database.select_all_cmp_lb,self.make_complete_lb_emb)
        dt = datetime.now(tz=timezone.utc)
        if skip and dt.hour == 12 and dt.minute <= 30:
            return
        data = await Database.select_all_cmp_lb()
        for d in data:
            timestamp = int(helpers.get_date_game(d.timeframe).timestamp())
            if skip and timestamp != d.timestamp:
                continue
            emb = await self.make_complete_lb_emb(d.guild_id, d.category, timestamp)
            if not emb:
                logger.warning("Could not make the embed for the guild %s", d.guild_id)
                continue
            if not await helpers.get_channel_and_edit(
                self.client, d.channel_id, d.message_id, embed=emb
            ):
                logger.info(
                    "Removing a member lb cause: channel not found: %s", d.channel_id
                )
                await Database.delete_cmp_lb(d.channel_id)

    async def make_complete_lb_emb(self, g_id: int, category: str, timestamp: int):
        try:
            guild = await SMMOApi.get_guild_info(g_id)
        except ApiError:
            return None
        if not guild:
            logger.warning("Could not retrive guild data from API")
            return None

        guild_members_mgr = GuildMembersManager(g_id)
        await guild_members_mgr.fetch_members()
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        var = []
        total = 0
        bulk_stats = await Database.select_user_stat_bulk(
            [m.user_id for m in guild_members_mgr.members.values()],
            dt.year,
            dt.month,
            dt.day,
        )
        for m in guild_members_mgr.members.values():
            if m.user_id in bulk_stats:
                stats = bulk_stats[m.user_id]
            else:
                stats = await Database.select_user_stat(
                    m.user_id, dt.year, dt.month, dt.day
                )
            if stats is None:
                value = None
            else:
                match category:
                    case "LEVELS":
                        value = m.level - stats.level
                    case "NPC":
                        value = m.npc_kills - stats.npc_kills
                    case "PVP":
                        value = m.user_kills - stats.user_kills
                    case "STEPS":
                        value = m.steps - stats.steps
                    case _:
                        value = 0
            total += value if value is not None else 0
            var.append({"id": m.user_id, "stat": value, "name": m.name})
        if len(var) == 0 or all(x["stat"] is None for x in var):
            return None

        emb = helpers.Embed(
            title=f"Members Complete leaderboard [{category}]",
            description=f"**Guild**: {guild.name}\n"
            f"**Stats**: from <t:{int(timestamp)}> - <t:{int(helpers.get_current_date_game().timestamp() + 86400)}>\n"
            f"**Last update**: <t:{int(datetime.now().timestamp())}:R>\n",
            thumbnail=f"https://simple-mmo.com/img/icons/{guild.icon}",
        )

        msg = ""
        need_title = True
        for i, player in enumerate(
            sorted(
                var,
                key=lambda member: member["stat"] if member["stat"] is not None else -1,
                reverse=True,
            ),
            1,
        ):
            # temp = f"[{player['name']}](https://simple-mmo.com/user/view/{player['id']}): {player["stat"]:,}\n"
            temp = f"{player['name']}: "

            temp += (
                f"{player['stat']:,}\n" if player["stat"] is not None else "No data\n"
            )
            if len(temp) + len(msg) <= 1024 and i % 10 != 0:
                msg += temp
            else:
                emb.add_field(
                    name="Members:" if need_title else "", value=msg, inline=False
                )
                need_title = False
                msg = temp
        if msg != "":
            emb.add_field(
                name="Members:" if need_title else "", value=msg, inline=False
            )
        return emb

    @loop(time=time(hour=14))
    async def eff(self):
        await self.set_new_gain_lb()
        await self.create_new_daily_leaderboard()

    @loop(minutes=10)
    async def update_season(self):
        logger.info("Check if new season is today")
        curr_season = await Database.select_last_season()
        end_time: datetime = datetime.fromisoformat(curr_season.ends_at[:-1])
        if end_time > datetime.now() + timedelta(days=1):
            logger.info("It's NOT")
            self.update_season.change_interval(time=time(hour=12))
            return
        logger.info("It is")
        new_seasons = tuple(await SMMOApi.get_guild_season())
        await Database.insert_season(
            new_seasons[-1].id,
            new_seasons[-1].name,
            new_seasons[-1].starts_at,
            new_seasons[-1].ends_at,
        )
        try:
            self.update_season.change_interval(
                time=time(hour=end_time.hour, minute=end_time.minute + 1)
            )
            self.update_guilds_end_season.start()
        except:
            logger.exception("Update season")
        logger.info("New seasons:\n%s", new_seasons)
        if datetime.fromisoformat(new_seasons[-1].starts_at[:-1]) < datetime.now():
            logger.info("Not YET")
            return
        logger.info("Adding new season into DB")
        self.update_season.change_interval(time=time(hour=12))

    @loop(time=time(hour=18, minute=29))
    async def update_guilds_end_season(self):
        from bot.discord_cmd.modules.guild._tasks import GuildTask

        logger.info("Updating gains lb for new season")
        gt = GuildTask(self.client)
        await gt.check_stats(end_season=True)
        logger.info("Sending new lb")
        await self.set_new_gain_lb()
        from asyncio import sleep

        logger.info("Sleeping waiting for new season to start")
        sleep(120)
        logger.info("updating new gains lb with new season info")
        await gt.check_stats(start_season=True)
        self.update_guilds_end_season.cancel()

    @loop(minutes=5)
    async def cleanup_msg(self):
        msgs = await Database.select_delmsg(int(datetime.now().timestamp()))
        for msg in msgs:
            try:
                channel = await self.client.fetch_channel(msg.chn_id)
                message = await channel.fetch_message(msg.msg_id)
                await message.delete()
            except NotFound:
                logger.warning("cleanup")
                continue
            except HTTPException:
                logger.exception("cleanup")
                continue
            except AttributeError:
                logger.exception("cleanup")
                continue
            finally:
                await Database.delete_delmsg(msg.msg_id, msg.chn_id)

    @loop(time=time(hour=12))
    async def set_new_gain_lb(self):
        data = await Database.select_all_gains_leaderboard()
        for d in data:
            emb = helpers.Embed(title="Loading leaderboard...")
            message = await helpers.get_channel_and_edit(
                self.client, d.channel_id, embed=emb
            )
            if not message or isinstance(message, bool):
                continue
            await Database.update_gains_leaderboard(d.channel_id, message.id)

    @loop(minutes=10.0)
    async def update_gains_lb(self):
        emb = await helpers.make_gains_emb()
        if not emb:
            return
        data = await Database.select_all_gains_leaderboard()
        for d in data:
            if not await helpers.get_channel_and_edit(
                self.client, d.channel_id, d.message_id, embed=emb
            ):
                logger.info(
                    "Removing a gains lb cause: channel not found: %s", d.channel_id
                )
                await Database.delete_gains_leaderboard(d.channel_id)

    @loop(time=time(hour=11, minute=59))
    async def create_new_daily_leaderboard(self):
        await self.update_leaderboards(False)
        await sleep(
            120
        )  # to have the date to the next day for helpers.get_current_date_game()
        data = await Database.select_all_lb()
        str_date = helpers.get_current_date_game().strftime("%d/%m/%Y")
        for d in data:
            if d.date == str_date:
                continue
            try:
                channel = await self.client.fetch_channel(d.channel_id)
                emb = helpers.Embed(
                    title="Loading leaderboard...\n*Now it should load 30/40min after the server reset*"
                )
                message = await channel.send(embed=emb)
                await Database.update_lb(
                    channel_id=channel.id,
                    message_id=message.id,
                    date=helpers.get_current_date_game().strftime("%d/%m/%Y"),
                )
            except NotFound:
                logger.info("Channel not found (create_new_daily_leaderboard)")
                logger.info(
                    "Removing a gains lb cause: channel not found: %s", d.channel_id
                )
                await Database.delete_lb(d.channel_id)
                continue
            except Forbidden:
                logger.info(
                    "Removing a gains lb cause: channel forbidden: %s", d.channel_id
                )
                await Database.delete_lb(d.channel_id)
                continue
            except HTTPException:
                logger.warning("Internet fault")
                continue

    @loop(minutes=10.0)
    async def update_leaderboards(self, skip: bool = True):
        current_date = helpers.get_current_date_game()
        dt = datetime.now(tz=timezone.utc)
        if skip and dt.hour == 12 and dt.minute <= 30:
            return
        data = await Database.select_all_lb()
        str_date = current_date.strftime("%d/%m/%Y")
        for d in data:
            if skip and str_date != d.date:
                await self.create_new_daily_leaderboard()
                continue
            emb = await helpers.make_members_lb(
                d.guild_id, d.date, current_date, task=True
            )
            if not emb:
                logger.warning("Could not make the embed for the guild %s", d.guild_id)
                continue
            if not await helpers.get_channel_and_edit(
                self.client, d.channel_id, d.message_id, embed=emb
            ):
                logger.info(
                    "Removing a member lb cause: channel not found: %s", d.channel_id
                )
                await Database.delete_lb(d.channel_id)

    @loop(time=time(hour=12))
    async def check_montly_reward(self):
        if datetime.now().day != 28:
            return
        pings = await Database.select_monthly_reward()
        # TODO: make emb with link for monthly reward
        for ping in pings:
            await helpers.get_channel_and_edit(
                self.client,
                channel_id=ping.channel_id,
                content=f"<@&{ping.role_id}> time to get monthly reward!\nGo to Town > Mahols Hut > Monthly Reward, to reedem it.",
            )

    @loop(minutes=30)
    async def activity_check(self):
        status_phrases = [
            "Bot still running... Maybe...",
            "Still alive and kicking.",
            "I haven't crashed yet! Surprising, I know.",
            "Just checking in. Still here.",
            "Beep boop. System is stable-ish.",
            "Running smoothly... don't jinx it.",
            "Current status: Not on fire.",
            "Alive, awake, alert, enthusiastic!",
            "Holding it together with digital duct tape.",
            "Still breathing in ones and zeros.",
            "No exception traces in sight.",
            "Operating within normal parameters. Probably.",
            "I think, therefore I compute.",
            "Still chugging along!",
            "Ghost in the machine is still haunting.",
            "Heartbeat detected. We are online.",
            "Still grinding away in the background.",
            "Uptime goes brrrrr.",
            "Server hamsters are still running on the wheel.",
            "Checking my pulse... yep, still alive.",
            "Still awake! Memory leak level: acceptable.",
            "Not dead yet!",
            "Doing bot things. You know how it is.",
            "Still here, plotting world domination... I mean, processing tasks.",
            "All systems go. More or less.",
            "Surviving another event loop iteration.",
            "Still standing, defying all odds.",
        ]

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {choice(status_phrases)}"
        )


def setup(client: Bot):
    client.add_cog(AdminTask(client))
