import discord
from bot.database import TrialDatabase
from bot.discord_cmd.helpers import helpers 
from bot.discord_cmd.helpers.logger import logger
from bot.discord_cmd.modules.trial._helper import send_log, LogType
class DeleteTrialButton(discord.ui.View):

    async def send(self, ctx: discord.ApplicationContext):
        self.emb = helpers.Embed(title=f"Delete {self.name} System?", description="This will delete the system, if you just want to disable it while keeping the settings try '/admin toggle_quest_system'")
        await ctx.followup.send(embed=self.emb, view=self)


    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if self.user != interaction.user.id:
            return await interaction.followup.send(content="No perms to use the button")

        await send_log(
            self.client,self.id,LogType.TRIAL_DELETION,
            value=self.name,
            usr1=self.user
        )

        await TrialDatabase.delete_trial(self.id)
        logger.info("Trial deleted: %s", self.name)
        self.disable_all_items()
        await interaction.response.edit_message(embed=helpers.Embed(title="Deleted"),view=self)
        await self.message.delete(delay=3)
        
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancell_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        if self.user != interaction.user.id:
            return await interaction.followup.send(content="No perms to use the button")
        self.disable_all_items()
        await interaction.response.edit_message(embed=helpers.Embed(title="Operation cancelled"),view=self)
        await self.message.delete(delay=5)

