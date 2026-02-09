import discord
from bot.discord_cmd.helpers import helpers 

class RequirementsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


    current_page: int = 1
    sep: int = 10
    type: int = 0
       
    async def send(self, ctx: discord.ApplicationContext):
        if len(self.data[1]) == 0:
            self.level_button.disabled = True
        if len(self.data[2]) == 0:
            self.npc_button.disabled = True
        if len(self.data[3]) == 0:
            self.pvp_button.disabled = True
        if len(self.data[4]) == 0:
            self.steps_button.disabled = True
        self.ctx = ctx
        self.message = await ctx.followup.send(view=self)
        await self.update_message(self.data[self.type][:self.sep])

    async def update_message(self, data):
        await self.update_buttons()
        try:
            await self.message.edit(embed=await self.create_embed(data), view=self)
        except discord.errors.Forbidden:
            await self.ctx.followup.send(content="Bot doesn't have the perms to see this channel, so the buttons of the message doesn't work.")


    async def update_buttons(self):
        if self.current_page == 1:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
            self.first_button.disabled = True
            self.first_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary
            self.first_button.disabled = False
            self.first_button.style = discord.ButtonStyle.green

        if self.current_page == int(len(self.data[self.type])/self.sep) + 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
            self.last_button.disabled = True
            self.last_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary
            self.last_button.disabled = False
            self.last_button.style = discord.ButtonStyle.green

    def get_current_page_data(self):
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        if self.current_page == 1:
            from_item = 0
            until_item = self.sep
        if self.current_page == int((len(self.data[self.type])) / self.sep) + 1:
            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data[self.type])
        return self.data[self.type][from_item:until_item]
    
    async def create_embed(self, data):
        title: list[str] = ["Activity","Levels","Npc","Pvp","Steps"]
        TEMPLATES:list[str] = ["".join(("Players inactive more than ",f"{f'{self.req.days} days' if self.req.days != 1 else 'one day'}:")),
                               "".join(("Players that have gained less than {value:,} {category} in ",f"{f'{self.req.days} days' if self.req.days != 1 else 'one day'}:")),
                               "[{name}](https://simple-mmo.com/user/view/{id}) last activity: <t:{value}:R>"]
        description: str = ""
        value: str = ""
        if self.type == 0:
            description = TEMPLATES[0]
            value = "\n".join(TEMPLATES[2].format(name=v["name"],id=v["id"],value=v["value"]) for v in data)
        elif self.type == 1 and len(self.data[self.type]) != 0:
            description = TEMPLATES[1].format(value=self.req.levels,category="levels")
            value = "\n".join(TEMPLATES[2].format(name=v["name"],id=v["id"],value=v["value"]) for v in data)
        elif self.type == 2 and len(self.data[self.type]) != 0:
            description = TEMPLATES[1].format(value=self.req.npc,category="npc kills")
            value = "\n".join(TEMPLATES[2].format(name=v["name"],id=v["id"],value=v["value"]) for v in data)
        elif self.type == 3 and len(self.data[self.type]) != 0:
            description = TEMPLATES[1].format(value=self.req.pvp,category="pvp kills")
            value = "\n".join(TEMPLATES[2].format(name=v["name"],id=v["id"],value=v["value"]) for v in data)
        elif self.type == 4 and len(self.data[self.type]) != 0:
            description = TEMPLATES[1].format(value=self.req.steps,category="steps")
            value = "\n".join(TEMPLATES[2].format(name=v["name"],id=v["id"],value=v["value"]) for v in data)
        else:
            description = "No requirement for this category"
            value = ""
            
        emb = helpers.Embed(title=title[self.type],description=description)
        emb.add_field(name="", value=value)
        emb.set_footer(text=f"Page {self.current_page}/{(len(self.data[self.type])) // self.sep + 1}{"\nStaff ignored" if self.ignore_staff else ""}")
        return emb
    
    @discord.ui.button(label="|<", style=discord.ButtonStyle.green)
    async def first_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        await self.update_message(self.get_current_page_data())
            

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page -= 1
        await self.update_message(self.get_current_page_data())


    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page += 1
        await self.update_message(self.get_current_page_data())


    @discord.ui.button(label=">|", style=discord.ButtonStyle.green)
    async def last_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = int(len(self.data[self.type]) / self.sep) + 1
        await self.update_message(self.get_current_page_data())

    
    @discord.ui.button(label="Activity", style=discord.ButtonStyle.blurple)
    async def activity_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Levels", style=discord.ButtonStyle.blurple)
    async def level_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Npc", style=discord.ButtonStyle.blurple)
    async def npc_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 2
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Pvp", style=discord.ButtonStyle.blurple)
    async def pvp_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 3
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Steps", style=discord.ButtonStyle.blurple)
    async def steps_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.type = 4
        await self.update_message(self.get_current_page_data())