import discord
from discord import TextChannel,SelectOption
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from bot.database import TrialDatabase
from bot.discord_cmd.modules.trial._helper import send_log, LogType, generate_info_emb
from bot.discord_cmd.modules.trial._entry_view import EntryView
from bot.discord_cmd.modules.trial._configure_task import ConfigureTaskView
from bot.discord_cmd.modules.trial._configure_category import ConfigureCategoryView
from bot.core._trial import TrialManager
from datetime import datetime


## Configure Trial
class ConfigureTrial(discord.ui.View):
    def __init__(self,tm,main):
        super().__init__(timeout=None)
        self.main = main
        self.tm = tm
        self.log_c = None
        self.ent_c = None
        self.not_c = None

    async def send(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.tm.trial.name} Configuration")
        emb.add_field(
            name="Overall Bot System",
            value=(
                f"From here you can change the system:\n"
                #f"- Name (is what give the commands the name).\n"
                #f"  > It can only be letters, numbers and '-','_'.\n"
                f"- Notify Channel.\n"
                f"  > It the channel used to send a ping to the user when they complete a task.\n"
                f"- Log Channel.\n"
                f"  > Is the channel where the bot will send the log about the system.\n"
                f"- Entry Channel.\n"
                f"  > The channel used to send a general message that allow to start tasks without having to type the command.\n"
                f"**Not setting a channel, even if it was already set, will remove those from the setting**"
            )
        )
        emb.add_field(
            name="Settings:",
            value=(
                f"Notify Channel: {f"<#{self.not_c}>" if self.not_c else 'Not Set'}\n"
                f"Log Channel: {f"<#{self.log_c}>" if self.log_c else 'Not Set'}\n"
                f"Entry Channel: {f"<#{self.ent_c}>" if self.ent_c else 'Not Set'}\n"
            ),
            inline=False
        )
        return emb

    @discord.ui.select(
        row = 1,
        placeholder="Notify Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select1_callback(self, select, interaction):
        await interaction.response.defer()
        self.not_c = select.values[0].id
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)


    @discord.ui.select(
        row = 2,
        placeholder="Log Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select2_callback(self, select, interaction):
        await interaction.response.defer()
        self.log_c = select.values[0].id
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)
        

    @discord.ui.select(
        row = 3,
        placeholder="Entry Channel",
        select_type=discord.ComponentType.channel_select
    )
    async def select3_callback(self, select, interaction):
        await interaction.response.defer()
        self.ent_c = select.values[0].id
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    #@discord.ui.button(label="Edit Name", style=discord.ButtonStyle.blurple, row=0)
    #async def edit_button(self, button:discord.ui.Button, interaction:discord.Interaction):
    #    await interaction.response.send_modal(EditNameModal(title="Edit System Name"))

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green,row=4)
    async def save_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        
        log = False
        if self.tm.trial.log_channel_id != self.log_c:
            log = True
            self.tm.trial.log_channel_id = self.log_c
        notif = False
        if self.tm.trial.notify_channel_id != self.not_c:
            notif = True
            self.tm.trial.notify_channel_id = self.not_c
        ent = False
        if self.tm.trial.entry_channel_id != self.ent_c:
            ent = True
            self.tm.trial.entry_channel_id = self.ent_c
        self.main.trial_changes = (self.tm.trial,(log,notif,ent))
        await self.main.restore_view(interaction)
        

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red,row=4)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await self.main.restore_view(interaction)

class ConfigureView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.trial_changes = None
        self.category_edits = []
        self.category_add = []
        self.category_removed = []
        self.task_edits = []
        self.task_add = []
        self.task_removed = []
        self.req_edits = []
        self.req_add = []
        self.req_removed = []

    async def send(self, ctx:discord.Interaction):
        await ctx.followup.send(embed=await self.create_embed(),view=self,ephemeral=True)

    async def restore_view(self, ctx:discord.Interaction):
        await ctx.edit_original_response(embed=await self.create_embed(),view=self)
        
    def update_btn(self):
        self.confirm_button.disabled = self.selected_t is None

    async def create_embed(self):
        emb = helpers.Embed(title=f"{helpers.make_title(self.tm.trial.name)} System Configuration")
        emb.add_field(
            name="Overall Bot System",
            value=(
                f"The System ({self.tm.trial.name}) works in _Categories_ and _Tasks_.\n"
                f"- The _Categories_ are group of tasks\n"
                f"- The _Tasks_ are what the user need to complete in order to recive a reward.\n"
                f"- The _Tasks_ can have different requisites and after completing all of them the bot will acknowledge the completation of a _Task_\n"
                f"\nTo create a _Task_ first create a _Category_.\n"
                f"\nSelect one of the buttons below to choose what configure, You will get more info about each customization in each setting.\n"
                f"The system can be disabled/enabled using `/{self.tm.trial.name} admin toggle`, and can be deleted using `/admin remove_quest_system` (this will delete all of the configuration and records from the database), use it only if you know what are you doing.\n"
                #f"_Below is shown what the system looks right now_"
            )
        )
        emb.set_footer(text="Note: Click Save to apply all changes")
        return emb

    @discord.ui.button(label="Edit System", style=discord.ButtonStyle.blurple,row=0)
    async def trial_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = ConfigureTrial(self.tm,self)
        await view.send(interaction)

    @discord.ui.button(label="Configure Category", style=discord.ButtonStyle.green,row=1)
    async def category_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = ConfigureCategoryView(self.tm,self)
        await view.send(interaction)

    @discord.ui.button(label="Configure Task", style=discord.ButtonStyle.green,row=2)
    async def task_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        view = ConfigureTaskView(self.tm,self)
        await view.send(interaction)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green,emoji="✔️",row=3)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()

        if self.trial_changes:
            self.tm.update("trial",self.trial_changes[0],False)
            if self.trial_changes[1][0]:
                await send_log(
                    interaction.client,self.tm.trial.server_id,LogType.TRIAL_UPDATE,
                    value=f"Log Channel",
                    extra_post=f"Log Channel is now {f"<#{self.log_c}>" if self.log_c else "Not Set"}",
                    usr1=interaction.user.id
                )
            if self.trial_changes[1][1]:
                await send_log(
                    interaction.client,self.tm.trial.server_id,LogType.TRIAL_UPDATE,
                    value=f"Notify Channel",
                    extra_post=f"Notify Channel is now {f"<#{self.not_c}>" if self.not_c else "Not Set"}",
                    usr1=interaction.user.id
                )
            if self.trial_changes[1][2]:
                await send_log(
                    interaction.client,self.tm.trial.server_id,LogType.TRIAL_UPDATE,
                    value=f"Entry Channel",
                    extra_post=f"Entry Channel is now {f"<#{self.ent_c}>" if self.ent_c else "Not Set"}",
                    usr1=interaction.user.id
                )
        for x in self.category_removed:
            if x in self.tm.categories:
                await send_log(
                    self.client,self.trial_mng.trial.server_id,LogType.CATEGORY_DELETION,
                    value=f"{self.trial_mng.categories[x].name.title()}",
                    usr1=interaction.user.id
                )
                del self.tm.categories[x]
            await TrialDatabase.delete_trial_category(x)
        for x in self.task_removed:
            if x in self.tm.tasks:
                await send_log(
                    self.client,self.trial_mng.trial.server_id,LogType.TASK_DELETION,
                    value=f"{self.trial_mng.tasks[x].name.title()}",
                    usr1=interaction.user.id
                )
                del self.tm.tasks[x]
            await TrialDatabase.delete_trial_task(x)
        for x in self.req_removed:
            if x in self.tm.requisites:
                del self.tm.requisites[x]
            await TrialDatabase.delete_trial_task_requisite(x)
        for x in self.category_edits:
            self.tm.update("category",x,False)
        for x in self.task_edits:
            self.tm.update("task",x,False)
        for x in self.req_edits:
            self.tm.update("requisite",x,False)
        await self.tm.save()
        await self.tm.fetch_categories(True)
        await self.tm.fetch_tasks(True)
        await self.tm.fetch_requisites(True)

        await interaction.followup.send("System Changes Saved",ephemeral=True)
        # Update Entry message
        entry = await TrialDatabase.select_trial_entry(self.tm.server_id)
        if entry:
            try:
                channel = await interaction.client.get_or_fetch(TextChannel,entry.channel_id)
                message = await channel.fetch_message(entry.message_id)
                await message.delete()
            except:
                logger.exception("While getting entry message")
        if self.tm.trial.entry_channel_id:
            try:
                channel = await interaction.client.get_or_fetch(TextChannel,self.tm.trial.entry_channel_id)
            except:
                logger.exception("error on fetch channel: %s",self.tm.trial.entry_channel_id)
                return
                
            view = EntryView(helpers.make_title(self.tm.trial.name),self.tm)
            msg = await channel.send(embed=await view.create_embed(),view=view)
            if entry:
                await TrialDatabase.update_trial_entry(self.tm.server_id,msg.id,channel.id)
            else:
                await TrialDatabase.insert_trial_entry(self.tm.server_id,msg.id,channel.id)
        else:
            await TrialDatabase.delete_trial_entry(trial_id=self.tm.trial.server_id)
        

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red,row=3)
    async def cancel_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(content="Configuration Close",embed=None,view=None)

