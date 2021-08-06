import asyncio
from discord_slash.utils.manage_commands import create_option
import lor_deckcodes
from data import DataDragon
import discord, os, json
from random import randint
from discord.ext import commands
from dotenv import load_dotenv
from lor_deckcodes import LoRDeck
from discord_slash import SlashCommand, ComponentContext, context
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

dd = DataDragon()

with open(os.path.join("data", "syntax.json"), "r") as f:
    syntx = json.load(f)

class Card():
    def __init__(self, locale, info):
        self.locale = locale
        self.data = self.get_data(locale, info)
        self.region = self.data["regionRef"]
        self.embed_list_size = len(self.data["associatedCardRefs"]) + 1
        self.id = 0
        self.embed_list = self.get_embed_list(locale)
    def get_data(self, locale, info):
        global dd
        info = info.lower()
        for s in dd.sets[locale]:
            for c in s:
                if (info == c["cardCode"].lower() or info == c["name"].lower()): 
                    return c
        raise CardError("Card not found")
    def get_icon_region(self, c):
        global dd
        for r in dd.globals[self.locale]["regions"]:
            if (c["regionRef"] == r["nameRef"]): 
                return r["iconAbsolutePath"]
    def get_set(self, c):
        global dd
        for s in dd.globals[self.locale]["sets"]:
            if (c["set"] == s["nameRef"]):
                return (f"{s['nameRef']} - {s['name']}", s["iconAbsolutePath"]) # name/icon of set
    def get_embed(self, c, num):
        with open("data/color.json", "r") as f:
            colour = json.load(f)
        embed = discord.Embed(description=f"*{c['flavorText']}*", color = int(f"0x{colour[self.region]}", 16))
        embed.set_author(name=f"({c['cost']}) {c['name']}", url=f"https://lor.mobalytics.gg/cards/{c['cardCode']}", icon_url=self.get_icon_region(c))
        embed.set_thumbnail(url=c["assets"][0]["gameAbsolutePath"])
        if (len(c["keywords"])):
            keywords_text = ", ".join(c["keywords"][:])
            embed.add_field(name=f"**{syntx[self.locale]['keywords']}**", value=keywords_text, inline=True)
        if (len(c["spellSpeed"])):
            embed.add_field(name=f"**{syntx[self.locale]['spellSpeed']}**", value=c["spellSpeed"], inline=True)
        if (len(c["descriptionRaw"])):
            embed.add_field(name=f"**{syntx[self.locale]['description']}**", value=c["descriptionRaw"], inline=False)
        if (len(c["levelupDescriptionRaw"])):
            embed.add_field(name=f"**{syntx[self.locale]['levelup']}**", value=c["levelupDescriptionRaw"], inline=False)
        if (c["type"] == "Unit"):
            embed.add_field(name=":crossed_swords: ", value=c["attack"], inline=True)
            embed.add_field(name=":heart: ", value=c["health"], inline=True)
        set_name, set_icon = self.get_set(c)
        embed.set_footer(text=f"{set_name} ({num + 1}/{self.embed_list_size})", icon_url=set_icon)
        return embed
    def get_embed_list(self, locale):
        elist = [self.get_embed(self.data, 0)]
        cnt = 1
        for refer in self.data["associatedCardRefs"]:
            elist.append(self.get_embed(self.get_data(locale, refer), cnt))
            cnt += 1
        return elist

class CardError(Exception):
    pass

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix = '!')
slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    print("Yawn...")

@slash.slash(name = "update", description = "Update bot's local data from the Riot's Data Dragon")
async def update(ctx):
    await ctx.send("Updating data from the Riot's Data Dragon. Please be patient for a while...")
    dd.update_data()
    await ctx.send(":white_check_mark: Update completed.")

@slash.slash(name = 'card', description = "Find your card based on your locale and card info (card code or name)", options=[create_option("locale", "Locale of your card", 3, True, ["en_us", "vi_vn"]), create_option("info", "Card code or name", 3, True)])
async def card(ctx: commands.Context, locale: str, info: str):
    mess_code = randint(0, 10000)
    c = Card(locale, info)
    c.id = 0
    buttons = [create_button(style = ButtonStyle.grey, label = "Back", emoji = '⬅️', custom_id = f"{mess_code}card_back"), create_button(style = ButtonStyle.grey, label = "Next", emoji = '➡️', custom_id = f"{mess_code}card_next")]
    action_row = create_actionrow(*buttons)
    mess = await ctx.send(embed = c.embed_list[c.id], components = [action_row])
    while True:
        react_ctx: ComponentContext = await wait_for_component(bot, components = [action_row])
        if (react_ctx.custom_id == f"{mess_code}card_back"):
            c.id -= 1
        elif (react_ctx.custom_id == f"{mess_code}card_next"):
            c.id += 1
        else: continue
        c.id %= c.embed_list_size
            # if (c.id >= c.embed_list_size): c.id = 0
        await react_ctx.edit_origin(embed = c.embed_list[c.id])
        # print(str(react_ctx.selected_options))
        # react, user = await bot.wait_for('reaction_add', check=check, timeout=30)


@bot.command(name = 'card')
async def card(ctx, locale, *args):
    if (locale == "en"): locale = "en_us"
    if (locale == "vi"): locale = "vi_vn"
    info = ' '.join(args[:])
    buttons = [create_button(style = ButtonStyle.grey, label = "Back", emoji = '⬅️', custom_id = "card_back"), create_button(style = ButtonStyle.grey, label = "Next", emoji = '➡️', custom_id = "card_next")]
    action_row = create_actionrow(*buttons)
    c = Card(locale, info)
    c.id = 0
    mess = await ctx.send(embed = c.embed_list[c.id], components = [action_row])
    while True:
        react_ctx: ComponentContext = await wait_for_component(bot, components = [action_row])
        if (react_ctx.custom_id == "card_back"):
            c.id -= 1
            if (c.id < 0): c.id = c.id = c.embed_list_size - 1
        else:
            c.id += 1
            if (c.id >= c.embed_list_size): c.id = 0
        await mess.edit(embed = c.embed_list[c.id])
        # print(str(react_ctx.selected_options))
        # react, user = await bot.wait_for('reaction_add', check=check, timeout=30)

@bot.event
async def on_commands_error(ctx, exc: Exception):
    if (isinstance(exc, CardError)): await ctx.send(":x: Card not found!")

bot.run(TOKEN)
