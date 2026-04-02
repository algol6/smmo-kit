import discord
from datetime import datetime
from bot.discord_cmd.helpers import helpers 

class MarketListView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.current_page: int = 1
        self.current_category: int = 0
        self.sep: int = 5
        self.categories_names:tuple[str] = ("Weapons","Armour","Items","Pets","Amulets","Shields","Boots","Helmets","Collectables","Avatars","Materials","Sprites","Greaves","Gaunlets","Backgrounds","Specials","Tools","Potions","Event Materials","Pleb","Misc")
        self.categories_icons:tuple[str] = (
            "https://simple-mmo.com/img/icons/W_Axe010.png",
            "https://simple-mmo.com/img/icons/A_Armor05.png",
            "https://simple-mmo.com/img/icons/I_Leaf.png",
            "https://simple-mmo.com/img/sprites/brownhorse.png",
            "https://simple-mmo.com/img/icons/Ac_Necklace05.png",
            "https://simple-mmo.com/img/icons/E_Wood03.png",
            "https://simple-mmo.com/img/icons/A_Shoes07.png",
            "https://simple-mmo.com/img/icons/HelmA0.png",
            "https://simple-mmo.com/img/icons/I_Eye.png",
            "https://simple-mmo.com/img/sprites/1.png",
            "https://simple-mmo.com/img/icons/one/icon893.png",
            "https://simple-mmo.com/img/icons/I_Cannon02.png",
            "https://simple-mmo.com/img/icons/two/32px/DarkGreaves_32.png",
            "https://simple-mmo.com/img/icons/content/mar-22/gauntlet/Icon4.png",
            "https://simple-mmo.com/img/bg/1.png",
            "https://simple-mmo.com/img/sprites/events/community-21/special/demonic-wings.png",
            "https://simple-mmo.com/img/icons/one/icon864.png",
            "https://simple-mmo.com/img/icons/one/icon277.png",
            "https://simple-mmo.com/img/sprites/events/community-21/items/ticket-bahamas.png",
            "https://simple-mmo.com/img/icons/S_Ice06.png",
            "https://simple-mmo.com/img/icons/I_Chest01.png"
        )
        self.SELLING_TEMPLATE: str = "**Seller**: {name}\n{description}\n**Price**: {price}\n[DM User In Game](https://web.simple-mmo.com/chat/private?user_id={smmo_id})\nListed: <t:{timestamp}:R>"

    async def send(self, ctx: discord.ApplicationContext):
        await ctx.followup.send(view=self)
        await self.update_message(None)

    async def update_message(self, data):
        await self.update_buttons()
        await self.message.edit(embed=await self.create_embed(data), view=self)
            
    async def update_buttons(self):
        if self.current_page == 1:
            self.prev_button.disabled = True
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.prev_button.disabled = False
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == len(self.data) - 1:
            self.next_button.disabled = True
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.next_button.style = discord.ButtonStyle.primary
        
    
    def get_current_page_data(self):
        until_item = self.current_page * self.sep
        from_item = until_item - self.sep
        if self.current_page == 1:
            from_item = 0
            until_item = self.sep
        if self.current_page == int((len(self.data[self.current_category]))/self.sep) + 1:
            from_item = self.current_page * self.sep - self.sep
            until_item = len(self.data[self.current_category])
        return self.data[self.current_category][from_item:until_item]

    async def create_embed(self, data):
        if data is None:
            return helpers.Embed(
                    title="No items found on this category",
                    description="Use '/market sell' to add your item"
                )
        emb:helpers.Embed = helpers.Embed(
            title=f"{self.categories_names[self.current_category]}'s Shop",
            thumbnail=self.categories_icons[self.current_category]
        )
        if len(data) == 0:
            emb.add_field(
                name="No Items in this category",
                value="Start selling your with '/market sell'",
                inline=False
            )
            return emb

        for item in data:
            price = f"{int(item.price):,}" if helpers.is_number(item.price) else item.price
            emb.add_field(
                name=item.title,
                value=self.SELLING_TEMPLATE.format(name=item.author_name,description=item.description,price=price,smmo_id=item.author_smmo_id,timestamp=item.time),
                inline=False
            )
        emb.set_footer(text=f"Page {self.current_page}/{int((len(self.data[self.current_category])) / self.sep) + 1}")
        return emb
    

    @discord.ui.select(
        placeholder="Select Category",
        options = [
            discord.SelectOption(label="Weapons",value="0"),
            discord.SelectOption(label="Armour",value="1"),
            discord.SelectOption(label="Items",value="2"),
            discord.SelectOption(label="Pets",value="3"),
            discord.SelectOption(label="Amulets",value="4"),
            discord.SelectOption(label="Shields",value="5"),
            discord.SelectOption(label="Boots",value="6"),
            discord.SelectOption(label="Helmets",value="7"),
            discord.SelectOption(label="Collectables",value="8"),
            discord.SelectOption(label="Avatars",value="9"),
            discord.SelectOption(label="Materials",value="10"),
            discord.SelectOption(label="Sprites",value="11"),
            discord.SelectOption(label="Greaves",value="12"),
            discord.SelectOption(label="Gaunlets",value="13"),
            discord.SelectOption(label="Backgrounds",value="14"),
            discord.SelectOption(label="Specials",value="15"),
            discord.SelectOption(label="Tools",value="16"),
            discord.SelectOption(label="Potions",value="17"),
            discord.SelectOption(label="Event Materials",value="18"),
            discord.SelectOption(label="Pleb",value="19"),
            discord.SelectOption(label="Misc",value="20",description="All the things that doesn't fit in the others categories"),
            ]
    )
    async def select_callback(self, select, interaction):
        await interaction.response.defer()
        self.current_category = int(select.values[0])
        for i in range(21):
            self.children[0].options[i].default = False
        self.children[0].options[self.current_category].default = True
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
        

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close_button(self, button:discord.ui.Button, interaction:discord.Interaction):
        await self.message.delete(delay=5)
    