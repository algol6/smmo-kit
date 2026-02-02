from discord import SlashCommandGroup
from discord.ext import commands

class CommandGroups(commands.Cog):
    group_admin = SlashCommandGroup(name="admin", description="Admin commands")
    admin_subgroup = group_admin.create_subgroup("admin")
    link_subgroup = group_admin.create_subgroup("link")
    role_subgroup = group_admin.create_subgroup("role")
    orphanage_subgroup = group_admin.create_subgroup("orphanage")
    diamonds_subgroup = group_admin.create_subgroup("diamonds")
    guild_subgroup = group_admin.create_subgroup("guilds")
    worldboss_subgroup = group_admin.create_subgroup("worldboss")
    event_subgroup = group_admin.create_subgroup("event")
    
    group_user = SlashCommandGroup(name="user", description="Users commands")

    group_guild = SlashCommandGroup(name="guild", description="Guilds commands")
    requirements_subgroup = group_guild.create_subgroup("requirement")
    members_subgroup = group_guild.create_subgroup("mbs")

    group_wb = SlashCommandGroup(name="worldboss", description="worldboss commands")
    set_subgroup = group_wb.create_subgroup("set")
    remove_subgroup = group_wb.create_subgroup("remove")

    group_bot = SlashCommandGroup(name="bot", description="Extra bot status commands")

    group_event = SlashCommandGroup(name="event", description="Events public commands")

    group_sg = SlashCommandGroup(name="sg", description="Shadow Garden exclusive commands")

    def __init__(self, client):
        self.client = client

def setup(client):
    client.add_cog(CommandGroups(client))