import discord
from bot.database import TrialDatabase
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.modules.trial._helper import send_log, LogType

class CancelTaskButton(discord.ui.View):
    def __init__(self,records,trial_mgr):
        super().__init__(timeout=None)
        self.trial_mgr = trial_mgr
        self.records = discord.ui.Select(
            row=0,
            placeholder=f"Choose a {helpers.make_title(self.trial_mgr.trial.name)}.",
            options=records
        )
        self.records.callback = self.select1_callback
        self.add_item(self.records)
        self.rec_id = None

    async def send(self, ctx: discord.ApplicationContext, emb):
        await ctx.followup.send(embed=emb, view=self)

    def update_btn(self):
        self.confirm_button.disabled = self.rec_id is None

    async def select1_callback(self,interaction:discord.Interaction):
        await interaction.response.defer()

        selected_value = self.records.values[0]

        for option in self.records.options:
            option.default = option.value == selected_value

        self.rec_id = int(selected_value)
        self.update_btn()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green,row=1,disabled=True)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await send_log(
            self.client,self.trial_mgr.trial.server_id,LogType.TASK_CANCELLED,
            value=f"{self.trial_mgr.categories[self.trial_mgr.tasks[self.trial_mgr.records[self.rec_id].trial_task_id].trial_category_id].name.title()} > {self.trial_mgr.tasks[self.trial_mgr.records[self.rec_id].trial_task_id].name.title()}",
            usr1=self.author_id,
            extra_post=f"\n**Reason**: Cancelled by user."
        )
        self.trial_mgr.records[self.rec_id].current_steps = self.player.steps
        self.trial_mgr.records[self.rec_id].current_npc = self.player.npc_kills
        self.trial_mgr.records[self.rec_id].current_pvp = self.player.user_kills
        self.trial_mgr.records[self.rec_id].current_levels = self.player.level
        self.trial_mgr.records[self.rec_id].update_time = self.timestamp
        self.trial_mgr.records[self.rec_id].cancelled = True
        await self.trial_mgr.update("record",self.trial_mgr.records[self.rec_id],True)
        await interaction.response.edit_message(embed=helpers.Embed(title=f"{helpers.make_title(self.trial_mgr.trial.name)} cancelled."))


    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancell_button(self, button:discord.ui.Button, interaction:discord.Interaction,row=1):
        self.disable_all_items()
        await interaction.response.edit_message(embed=helpers.Embed(title="Operation cancelled"))
