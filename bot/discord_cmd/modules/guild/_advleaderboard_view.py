import discord
from bot.discord_cmd.helpers import helpers 

class AdvleaderboardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    current_page: int = 1
    sep: int = 10

    async def on_timeout(self):
        self.disable_all_items()
        self.prev_button.style = discord.ButtonStyle.gray
        self.next_button.style = discord.ButtonStyle.gray
        self.first_button.style = discord.ButtonStyle.gray
        self.last_button.style = discord.ButtonStyle.gray
        self.all_button.style = discord.ButtonStyle.gray
        self.tier1_button.style = discord.ButtonStyle.gray
        self.tier2_button.style = discord.ButtonStyle.gray
        self.tier3_button.style = discord.ButtonStyle.gray
        self.tier4_button.style = discord.ButtonStyle.gray
        self.tier5_button.style = discord.ButtonStyle.gray
        self.tier6_button.style = discord.ButtonStyle.gray
        self.tier7_button.style = discord.ButtonStyle.gray


    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.tier = 0
        self.data_type = 0
        self.message = await ctx.followup.send(view=self)
        await self.update_message(self.data[self.tier][self.data_type][:self.sep])
        

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

        if self.current_page == int(len(self.data[self.tier][self.data_type])/self.sep) + 1:
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
        if self.current_page == int((len(self.data[self.tier][self.data_type])) / self.sep) + 1:
            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data[self.tier][self.data_type])
        return self.data[self.tier][self.data_type][from_item:until_item]
    

    async def create_embed(self, data):
        tiers_name:tuple[str] = ("All","Tier 1 (Levels 1-25)","Tier 2 (Levels 26-100)","Tier 3 (Levels 101-500)","Tier 4 (Levels 501-1,000)","Tier 5 (Levels 1,001-5,000)","Tier 6 (Levels 5,001-10,000)","Tier 7 (Levels 10,001-99,999,999+)")
        colors:tuple[hex] = (None,0x00f6ff,0xf1c40f,0x8e44ad,0xc0392b,0xe67e22,0x2980b9,0x34495e)

        emb = helpers.Embed(title=f"{tiers_name[self.tier]} - {('NPC','PVP','Steps','Levels')[self.data_type]}",
                            description=f"Stats from <t:{self.start_data}> to <t:{self.end_data}>",
                            color=colors[self.tier])
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        if len(data) != 0:
            emb.add_field(name="", value="\n".join([f"#{i} [{v['name']}](https://simple-mmo.com/user/view/{v['id']}): {v['stats']:,}" for v,i in zip(self.data[self.tier][self.data_type][from_item:until_item],range(from_item + 1, until_item + 1))]))
        else:
            emb.add_field(name="", value="No members in this tier")
        emb.set_footer(text=f"Page {self.current_page}/{(len(self.data[self.tier][self.data_type])) // self.sep + 1}")
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
        self.current_page = int((len(self.data[self.tier][self.data_type])) / self.sep) + 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="All", style=discord.ButtonStyle.primary)
    async def all_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="NPC", style=discord.ButtonStyle.green)
    async def npc_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.data_type = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="PVP", style=discord.ButtonStyle.green)
    async def pvp_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.data_type = 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="STEPS", style=discord.ButtonStyle.green)
    async def steps_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.data_type = 2
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="LEVELS", style=discord.ButtonStyle.green)
    async def levels_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.data_type = 3
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 1", style=discord.ButtonStyle.primary)
    async def tier1_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 2", style=discord.ButtonStyle.primary)
    async def tier2_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 2
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 3", style=discord.ButtonStyle.primary)
    async def tier3_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 3
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 4", style=discord.ButtonStyle.primary)
    async def tier4_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 4
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 5", style=discord.ButtonStyle.primary)
    async def tier5_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 5
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 6", style=discord.ButtonStyle.primary)
    async def tier6_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 6
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Tier 7", style=discord.ButtonStyle.primary)
    async def tier7_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 7
        await self.update_message(self.get_current_page_data())