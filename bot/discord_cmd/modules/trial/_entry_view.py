import discord
from bot.discord_cmd.helpers import helpers 
from bot.discord_cmd.helpers.logger import logger
from bot.database import TrialDatabase 
from datetime import datetime
from bot.discord_cmd.modules.trial._helper import generate_info_emb
from bot.discord_cmd.modules.trial._accept_task_view import AcceptTaskView
from bot.core._trial import TrialManager
from discord import SelectOption

class EntryView(discord.ui.View):
    def __init__(self,label:str="Start Task",trial_manager=None):
        super().__init__(timeout=None)
        self.tm = trial_manager
        self.start_button = discord.ui.Button(
            row=0,
            label=f"Start {label}",
            style=discord.ButtonStyle.green,
            custom_id="start-trial-btn"
        )
        self.start_button.callback = self.start_button_callback
        self.add_item(self.start_button)


    async def send(self, ctx: discord.Interaction):
        await ctx.followup.send(view=self)
        if not await TrialDatabase.insert_trial_entry(self.tm.trial.server_id,self.message.channel.id,self.message.id):
            logger.error("Could not update the entry message for: %s",self.tm.trial.name)
        await self.update_message()
        
    async def update_message(self):
        await self.message.edit(embed=await self.create_embed(), view=self)

    async def create_embed(self):
        try:
            emb = await generate_info_emb(self.tm.trial.server_id)
        except AttributeError:
            self.tm = TrialManager(self.message.guild.id)
            await self.tm.fetch_trial()
            emb = await generate_info_emb(self.tm.trial.server_id)
        return emb

    async def start_button_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        ig_user = await helpers.get_user(user=interaction.user)
        if ig_user is None:
            return await interaction.followup.send("You are not linked with the bot. Use '/user verify' to link.",ephemeral=True)
        trial_mng = TrialManager(interaction.guild_id)
        await trial_mng.fetch_requisites()
        await trial_mng.fetch_records()

        if not trial_mng.trial.enabled:
            return await interaction.followup.send(
                content="```System temporarily disabled.```",
                ephemeral=True
            )
        if trial_mng.trial.guild_id != ig_user.guild.id:
            return await interaction.followup.send(
                content="```You need to be member of the guild to use the system.```",
                ephemeral=True
            )

        options_categories = []
        if not trial_mng.categories:
            options_categories.append(SelectOption(label="None"))
        else:
            for cat in trial_mng.categories.values():
                options_categories.append(SelectOption(label=cat.name.title(),value=str(cat.id)))
   
        view = AcceptTaskView(options_categories)
        view.trial_mng = trial_mng
        view.client = interaction.client
        view.author_id = interaction.user.id
        view.ig_user = ig_user
        
        await view.send(interaction)