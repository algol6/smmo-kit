import discord
from bot.discord_cmd.helpers import helpers
from bot.discord_cmd.helpers.logger import logger
from datetime import datetime,timezone
from bot.discord_cmd.modules.event._preview_registration_view import PreviewRegistrationView

class RegistrationModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Name",placeholder="The name of the event. ex: The Greatest Event Ever Done"))
        self.add_item(discord.ui.InputText(label="Event Formula",placeholder="Use 'NPC','STEPS' or 'PVP' as variable. ex: NPC*30 + STEPS*3"))
        self.add_item(discord.ui.InputText(label="Starting Date (On server reset of that day)",placeholder="Use DD/MM/YYYY format. ex: 18/11/2026"))
        self.add_item(discord.ui.InputText(label="Ending Date (On server reset of that day)",placeholder="Use DD/MM/YYYY format. ex: 1/1/2027"))
        self.add_item(discord.ui.InputText(label="Description (optional)",placeholder="", required=False,style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        self.name = self.children[0].value
        self.formula = self.children[1].value
        self.s_date = self.children[2].value
        self.e_date = self.children[3].value
        self.description = self.children[4].value
        

        s_date = helpers.get_date_game(self.s_date)
        e_date = helpers.get_date_game(self.e_date)

        if s_date is None or e_date is None:
           return await interaction.respond(content="Wrong date format in 'starting_date' or 'ending_date'. use dd/mm/yyyy format")
        if s_date <= datetime.now(tz=timezone.utc):
            return await interaction.respond(content="Start date can't be before the current date.")
        if e_date <= s_date:
            return await interaction.respond(content="End date can't be before the start date.")
        if self.formula!=" ":
            temp_step = 5
            temp_npc = 1
            temp_pvp = 2
            message = helpers.evaluate_formula(self.formula, temp_step, temp_npc, temp_pvp)
            if not helpers.is_number(message):
                return await interaction.followup.send(content=message)
            message = f"Formula tested with some test stats\nSteps: 5\nNPC: 1\nPVP: 2\nFormula: ```{self.formula.upper()}```\nResult with Formula: {message}\n"
        else:
            self.formula = "None"
        
        view = PreviewRegistrationView()
        view.player = self.player
        view.author_id = self.author_id
        view.name = self.name
        view.desc = self.description
        view.custom_image = self.custom_image
        view.custom_thumbnail = self.custom_thumbnail
        view.s_date = s_date
        view.e_date = e_date
        view.event_formula = self.formula
        view.team_size = self.team_size
        view.igguild_id = self.igguild_id
        await view.send(interaction,content=f"Teams Size: {self.team_size}")