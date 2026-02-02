import discord
from bot.discord_cmd.helpers import helpers 

class ContributionView(discord.ui.View):
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
        self.power_point.style = discord.ButtonStyle.gray
        self.gold.style = discord.ButtonStyle.gray
        self.gxp.style = discord.ButtonStyle.gray


    async def send(self, ctx: discord.ApplicationContext):
        self.ctx = ctx
        self.tier = 0
        self.message = await ctx.followup.send(view=self)
        await self.update_message(self.data[self.tier][:self.sep])
        

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

        if self.current_page == int(len(self.data[self.tier])/self.sep) + 1:
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
        if self.current_page == int((len(self.data[self.tier])) / self.sep) + 1:
            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data[self.tier])
        return self.data[self.tier][from_item:until_item]
    

    async def create_embed(self, data):
        tiers_name:list[str] = ["Power Point","Gold","Gxp","Guild Bank","Sanctuary"]
        thumbnail:list[str] = ["https://simple-mmo.com/img/icons/one/icon139.png","https://simple-mmo.com/img/icons/I_GoldCoin.png","https://simple-mmo.com/img/icons/S_Light01.png","https://web.simple-mmo.com/img/icons/one/icon367.png","https://web.simple-mmo.com/img/icons/two/32px/CoinGold1_32.png"]
        colors:list[hex] = [0xc0392b,0xe67e22,0x2980b9,0xffe886,0xffec9d]
        desc = ""
        if self.tier == 3:
            desc = f"Total tax collected: {sum(x["stats"] for x in self.data[self.tier]):,}"
        elif self.tier == 4:
            desc = f"Total Sanctuary contributed: {sum(x["stats"] for x in self.data[self.tier]):,}"

        emb = helpers.Embed(title=f"{tiers_name[self.tier]}",
                            color=colors[self.tier],
                            description=desc,
                            thumbnail=thumbnail[self.tier])
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        
        emb.add_field(name="", value="\n".join([f"#{i} [{v["name"]}](https://simple-mmo.com/user/view/{v["id"]}): {format(v["stats"],",d")}" for v,i in zip(self.data[self.tier][from_item:until_item],range(from_item + 1, until_item + 1))]))
    
        emb.set_footer(text=f"Page {self.current_page}/{(len(self.data[self.tier])) // self.sep + 1}")
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
        self.current_page = int((len(self.data[self.tier])) / self.sep) + 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Power Points", style=discord.ButtonStyle.primary)
    async def power_point(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 0
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Gold", style=discord.ButtonStyle.primary)
    async def gold(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 1
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Gxp", style=discord.ButtonStyle.primary)
    async def gxp(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 2
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Guild Bank", style=discord.ButtonStyle.primary)
    async def guild_bank(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 3
        await self.update_message(self.get_current_page_data())

    @discord.ui.button(label="Sanctuary", style=discord.ButtonStyle.primary)
    async def sanctuary(self, button:discord.ui.Button, interaction:discord.Interaction):
        await interaction.response.defer()
        self.current_page = 1
        self.tier = 4
        await self.update_message(self.get_current_page_data())