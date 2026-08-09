from discord import Bot,ApplicationContext,slash_command,guild_only,option,Member,SelectOption,SlashCommand,SlashCommandGroup
from discord.ext.commands import Cog
from pycord.multicog import subcommand

from datetime import time, datetime, timezone, timedelta
from bot.api import SMMOApi
from bot.database import TrialDatabase
from bot.core._trial import TrialManager
from bot.discord_cmd.helpers import permissions,command_utils,helpers
from bot.discord_cmd.modules.trial._tasks import TrialTask
from bot.discord_cmd.modules.trial._accept_task_view import AcceptTaskView
from bot.discord_cmd.modules.trial._trial_system_view import TrialSetUpView
from bot.discord_cmd.modules.trial._configure_view import ConfigureView
from bot.discord_cmd.modules.trial._confirm_delete_trial_view import DeleteTrialButton
from bot.discord_cmd.modules.trial._confirm_cancel_task_view import CancelTaskButton
from bot.discord_cmd.modules.trial._helper import send_log,LogType,generate_status_emb,generate_info_emb

## TODO: make decorator to check if the user is in the guild and if the trial is enabled
class Trial(Cog):
    def __init__(self, client):
        self.client = client

    @staticmethod
    async def generate_trial_tree(client,server_settings:dict):
        if server_settings is None:
            return

        for custom_name, guilds_id in server_settings.items():
            main_group = SlashCommandGroup(
                name=custom_name,
                description=f"Main commands for {custom_name}",
                guild_ids=guilds_id
            )

            main_group.add_command(SlashCommand(
                func=Trial.start,
                name="start",
                description="Select and start a task",
                parent=main_group
            ))
            main_group.add_command(SlashCommand(
                func=Trial.cancel,
                name="cancel",
                description="Cancel current task",
                parent=main_group
            ))
            main_group.add_command(SlashCommand(
                func=Trial.status,
                name="status",
                description="Get info about your current task",
                parent=main_group
            ))
            main_group.add_command(SlashCommand(
                func=Trial.info,
                name="info",
                description=f"Show info about the {custom_name} system",
                parent=main_group
            ))

            admin_subgroup = main_group.create_subgroup(
                name="admin",
                description=f"Settings for {custom_name}"
            )
            admin_subgroup.add_command(SlashCommand(
                func=Trial.toggle,
                name="toggle",
                description=f"Enable/Disable the {custom_name}",
                parent=admin_subgroup
            ))
            admin_subgroup.add_command(SlashCommand(
                func=Trial.configure,
                name="configure",
                description=f"Add a new category to {custom_name}",
                parent=admin_subgroup
            ))

            # TODO: 1CHECK IF POINT OF A TRIAL ARE ENABLED IF YES ADD admin set_points

            client.add_application_command(main_group)
            await client.sync_commands()

    @subcommand("admin")
    @slash_command(description="Create your guild quest system")
    @guild_only()
    @option(name="name", description="This will be the name of the commands related to your system")
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/admin create_quest_system")
    @command_utils.took_too_long()
    async def create_quest_system(self, ctx:ApplicationContext, name:str) -> None:
        name = name.strip()
        if not helpers.allowed_name(name):
            return await helpers.send(ctx,"Name not allowed only letters, digits or '-' and '_' ")

        view = TrialSetUpView()
        view.generate_trial_tree = self.generate_trial_tree
        view.server_id = ctx.guild_id
        view.guild_id = ctx.game_guild_id
        view.name = name
        view.author_id = ctx.author.id
        view.client = self.client
        view.generate_commands = self.generate_trial_tree
        await view.send(ctx)

    @subcommand("admin")
    @slash_command(description="This will delete the quest system on this server")
    @guild_only()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.auto_defer(False)
    @command_utils.statistics("/admin remove_quest_system")
    @command_utils.took_too_long()
    async def remove_quest_system(self, ctx:ApplicationContext) -> None:
        trial = await TrialDatabase.select_trial_by_server_id(ctx.guild_id)
        if trial is None:
            return await helpers.send(ctx,"No quest system setted on this server")

        view = DeleteTrialButton()
        view.client = self.client
        view.user = ctx.author.id
        view.name = trial.name
        view.id = trial.server_id
        await view.send(ctx)

    @command_utils.auto_defer()
    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @command_utils.statistics("/custom_quest admin toggle")
    @command_utils.took_too_long()
    @staticmethod
    async def toggle(ctx:ApplicationContext, enable:bool) -> None:
        trial = await TrialDatabase.select_trial_by_server_id(ctx.guild_id)
        if trial is None:
            return await helpers.send(ctx,"No quest system setted on this server")
        await TrialDatabase.update_trial(trial.server_id,trial.log_channel_id,trial.notify_channel_id,trial.entry_channel_id,trial.name,enable)
        await send_log(ctx.bot,ctx.guild_id,LogType.TRIAL_TOGGLE,'Enabled' if enable else 'Disabled',ctx.author.id)
        await helpers.send(ctx,content=f"Your System has been {'Enabled' if enable else 'Disabled'}")


    @command_utils.auto_defer()
    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.statistics("/custom_quest start")
    @command_utils.trial_user()
    @command_utils.took_too_long()
    @staticmethod
    async def start(ctx:ApplicationContext) -> None:
        trial_mng = TrialManager(ctx.guild_id,ctx.trial)
        await trial_mng.fetch_requisites()
        await trial_mng.fetch_records()

        options_categories = []
        if not trial_mng.categories:
            options_categories.append(SelectOption(label="None"))
        else:
            for cat in trial_mng.categories.values():
                options_categories.append(SelectOption(label=cat.name.title(),value=str(cat.id)))


        view = AcceptTaskView(options_categories)
        view.trial_mng:TrialManager = trial_mng
        view.client = ctx.bot
        view.author_id = ctx.author.id
        view.ig_user = ctx.ig_user
        await view.send(ctx)

    @command_utils.auto_defer()
    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.statistics("/custom_quest status")
    @command_utils.trial_user()
    @command_utils.took_too_long()
    @staticmethod
    async def status(ctx:ApplicationContext,user:Member=None) -> None:
        trial_mgr = TrialManager(ctx.guild_id,ctx.trial)
        await trial_mgr.fetch_records()
        ig_user = ctx.ig_user if user is None else await helpers.get_user(user=user)
        records = await trial_mgr.fetch_user_active_records(ig_user.id)
        records.update({x.id:x for x in (await trial_mgr.fetch_user_last_records(ig_user.id,True)).values()})
        emb = await generate_status_emb(records,ig_user,helpers.make_title(trial_mgr.trial.name),True)
        await helpers.send(ctx,embed=emb)


    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.auto_defer()
    @command_utils.statistics("/custom_quest cancel")
    @command_utils.trial_user()
    @command_utils.took_too_long()
    @staticmethod
    async def cancel(ctx:ApplicationContext) -> None:
        trial_mgr = TrialManager(ctx.guild_id)
        await trial_mgr.fetch_records()
        active_records = await trial_mgr.fetch_user_active_records(ctx.ig_user.id)
        if not active_records:
            return await helpers.send(ctx,"No task active")

        tasks_selection = []
        for rec in active_records.values():
            tasks_selection.append(SelectOption(label=trial_mgr.tasks[rec.trial_task_id].name.title(),value=str(rec.id)))

        emb = await generate_status_emb(active_records,ctx.ig_user,helpers.make_title(trial_mgr.trial.name))
        emb.thumbnail=""
        emb.description=""
        emb.title="Cancel one of the current active tasks?"

        view = CancelTaskButton(tasks_selection,trial_mgr)
        view.timestamp = int(datetime.now().timestamp())
        view.player = ctx.ig_user
        view.author_id = ctx.author.id
        view.client = ctx.bot
        await view.send(ctx,emb)

    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.auto_defer(False)
    @command_utils.trial_enabled()
    @command_utils.statistics("/custom_quest info")
    @command_utils.took_too_long()
    @staticmethod
    async def info(ctx:ApplicationContext) -> None:
        emb = await generate_info_emb(ctx.trial.server_id)
        return await helpers.send(ctx,embed=emb)

    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.auto_defer()
    @command_utils.trial_enabled()
    @command_utils.statistics("/custom_quest admin configure")
    @command_utils.took_too_long()
    @staticmethod
    async def configure(ctx:ApplicationContext) -> None:
        # LEVEL REQ can be done only if alone. No LVL+STEPS, only "LVL"
        trial_mng = TrialManager(ctx.guild_id,ctx.trial)
        await trial_mng.fetch_requisites()

        view = ConfigureView()
        view.tm = trial_mng
        await view.send(ctx)

    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.auto_defer()
    @command_utils.trial_enabled()
    @command_utils.statistics("/custom_quest admin remove_task")
    @command_utils.took_too_long()
    @staticmethod
    async def remove_task(ctx:ApplicationContext) -> None:
        await helpers.send(ctx,"WIP")

    @permissions.require_admin_or_staff()
    @permissions.require_linked_server()
    @permissions.require_linked_account()
    @command_utils.auto_defer()
    @command_utils.trial_enabled()
    @command_utils.statistics("/custom_quest admin set_points")
    @command_utils.took_too_long()
    @staticmethod
    async def set_points(ctx:ApplicationContext) -> None:
        await helpers.send(ctx,"WIP")


def setup(client:Bot):
    client.add_cog(Trial(client))
    client.add_cog(TrialTask(client))
