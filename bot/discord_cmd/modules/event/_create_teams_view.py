import discord
from bot.discord_cmd.helpers import helpers
from bot.database import Database
from math import ceil

class CreateTeamsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.s_user = None
        self.s_team = None

        self.users_select = None
        self.team_select = None

    async def send(self, ctx: discord.ApplicationContext):
        await self.generate_select_menu()
        await ctx.followup.send(embed=await self.create_embed(),view=self)        

    async def update_buttons(self):
        self.add_button.disabled = not (self.s_user and self.s_team)

    async def create_embed(self):
        emb = helpers.Embed(title=f"{self.evt.name}")

        msg = ""
        for i,user in enumerate(self.partecipants,1):
            msg += f"{user.name}[{user.smmo_id}] - {"No Team" if user.team == "" else f"Team {user.team}"}\n"
            if i%5==0:
                emb.add_field(
                    name="",
                    value=msg,
                    inline=False
                )
                msg=""
        
        if msg != "":
            emb.add_field(
                    name="",
                    value=msg,
                    inline=False
                )
        return emb  

    async def generate_select_menu(self):
        self.partecipants = tuple(await Database.select_event_partecipants(self.evt.id))
        options = []
        for x in self.partecipants:
            if x.team=="" and len(options)<25:
                options.append(discord.SelectOption(label=x.name,value=str(x.smmo_id)))

        if len(options) == 0:
            options = [discord.SelectOption(label="None")]
        if self.users_select is None:
            self.users_select = discord.ui.Select(
                custom_id="participant-selection",
                row=0,
                placeholder="Choose a Participant...",
                options=options
            )
            self.users_select.callback = self.select1_callback
            self.add_item(self.users_select)
        else:
            self.users_select.options = options

        options = []
        max_size = self.evt.team_size
        existing_teams = {}
        unassigned_count = 0
        
        for p in self.partecipants:
            if p.team != "":
                if p.team not in existing_teams:
                    existing_teams[p.team] = []
                existing_teams[p.team].append(p)
            else:
                unassigned_count += 1

        leftover_people = unassigned_count
        for team_id in existing_teams:
            members = existing_teams[team_id]
            spots_available = max_size - len(members)
            leftover_people -= min(leftover_people, spots_available)

        new_teams_needed = ceil(leftover_people / max_size) if leftover_people > 0 else 0
        
        for t_num in sorted(existing_teams.keys(), key=int):
            members = existing_teams[t_num]
            if len(members) < max_size and len(options)<=25:
                options.append(discord.SelectOption(label=f"Team {t_num} [{len(members)}/{max_size}]", value=str(t_num)))

        last_team_num = int(max(existing_teams.keys(), key=int)) if existing_teams else 0
        for i in range(1, new_teams_needed + 1):
            if len(options)<25:
                options.append(discord.SelectOption(label=f"Team {last_team_num + i} [0/{max_size}]", value=str(last_team_num + i)))

        if len(options) == 0:
            options = [discord.SelectOption(label="None")]
        
        if self.team_select is None:
            self.team_select = discord.ui.Select(
                custom_id="team-selection",
                row = 1,
                placeholder="Choose a Team...",
                options=options
            )
            self.team_select.callback = self.select2_callback
            self.add_item(self.team_select)
        else:
            self.team_select.options = options

    async def select1_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.users_select.values[0]
        for option in self.users_select.options:
            option.default = option.value == selected_value
        self.s_user = int(selected_value)

        await self.update_buttons()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)


    async def select2_callback(self, interaction:discord.Interaction):
        await interaction.response.defer()
        selected_value = self.team_select.values[0]
        for option in self.team_select.options:
            option.default = option.value == selected_value
        self.s_team = selected_value

        await self.update_buttons()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)

    @discord.ui.button(label="Add To The Team", style=discord.ButtonStyle.green, disabled=True,row=2)
    async def add_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await Database.update_event_partecipant(self.s_user,self.evt.id,self.s_team)
        self.s_user = None
        self.s_team = None
        await self.generate_select_menu()
        await self.update_buttons()
        await interaction.edit_original_response(embed=await self.create_embed(),view=self)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.red,row=2)
    async def close_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(content="Closed",embed=None,view=None)
