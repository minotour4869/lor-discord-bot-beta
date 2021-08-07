import asyncio
from discord.ext.commands.context import Context
from discord_slash.utils.manage_commands import create_option
import lor_deckcodes
from data import DataDragon
import discord, os, json
import random
from random import randint
from discord.ext import commands
from dotenv import load_dotenv
from lor_deckcodes import LoRDeck
from discord_slash import SlashCommand, ComponentContext, context
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle
from datetime import datetime
import binascii

dd = DataDragon()

with open(os.path.join("data", "syntax.json"), "r") as f:
    syntx = json.load(f)

class Card():
    def __init__(self, locale, info):
        self.locale = locale
        self.data = self.get_data(locale, info)
        self.region_short = ""
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
                self.region_short = r["abbreviation"]
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

class Deck():
    def __init__(self, user: discord.User, locale, deckcode, deckname):
        self.user = user
        self.locale = locale
        self.deckcode = deckcode
        self.decklist = LoRDeck.from_deckcode(deckcode)
        self.deckname = deckname if (deckname != "") else syntx[locale]["did"]
    def get_data(self):
        op = {
            "chs": "",
            "fls": "",
            "sps": "",
            "lms": ""
        }
        regions = []
        for card in self.decklist:
            text = ""
            c = Card(self.locale, card[2:])
            # print(type(c.data))
            if (c.data['region'] not in regions): regions.append(c.data["region"])
            rarity = c.data["rarityRef"].upper()[0:2]
            region = c.region_short
            text += f"<:{region}:{syntx['emote'][region]}> <:{rarity}:{syntx['emote'][rarity]}> {card[0]}x {c.data['name']}\n"
            if (c.data["type"] == syntx[self.locale]["sp"]): op[f"sps"] += text
            elif (c.data["type"] == syntx[self.locale]["lm"]): op[f"lms"] += text
            elif (c.data["supertype"] == syntx[self.locale]["ch"]): op[f"chs"] += text
            else: op[f"fls"] += text
        return op, regions
    def get_embed(self):
        data, regions = self.get_data()
        region_text = "/".join(regions[:])
        embed = discord.Embed(title = self.deckname, description = f"**{syntx[self.locale]['rg']}:** {region_text}", url = f'https://lor.mobalytics.gg/decks/code/{self.deckcode}', timestamp = datetime.now())
        embed.set_footer(icon_url = self.user.avatar_url, text = f'by {str(self.user)}')
        if (len(data["chs"])): embed.add_field(name = syntx[self.locale]["chs"], value = data["chs"], inline = True)
        if (len(data["fls"])): embed.add_field(name = syntx[self.locale]["fls"], value = data["fls"], inline = True)
        if (len(data["sps"])): embed.add_field(name = syntx[self.locale]["sps"], value = data["sps"], inline = True)
        if (len(data["lms"])): embed.add_field(name = syntx[self.locale]["lms"], value = data["lms"], inline = True)
        return embed

class CardError(Exception):
    pass

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
bot = commands.Bot(command_prefix = '!')
slash = SlashCommand(bot, sync_commands=True)

@bot.event
async def on_ready():
    print("Yawn...")

@slash.slash(name = 'card', description = "Find your card based on your locale and card info (card code or name)", options = [create_option("locale", "Locale of your card", 3, True, ["en_us", "vi_vn"]), create_option("info", "Card code or name", 3, True)])
async def card(ctx: commands.Context, locale: str, info: str):
    mess_code = randint(0, 1000000)
    try:
        c = Card(locale, info)
    except Exception as err:
        if (isinstance(err, CardError)):
            await ctx.send(f':x: {syntx[locale]["cardnotfound"]}', hidden = True)
        await ctx.send(":x: Unexpected error found, please contact the developer for more information.", hidden = True)
        return
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

@slash.slash(name = "deck", description = "Get the information of a decklist via deckcode", options = [create_option("locale", "Locale of your card", 3, True, ["en_us", "vi_vn"]), create_option("deckcode", "Deckcode", 3, True), create_option("name", "Name of your deck", 3, False)])
async def deck(ctx: Context, locale, deckcode, deckname = ""):
    try:
        deck = Deck(ctx.author, locale, deckcode, deckname)
        await ctx.send(embed = deck.get_embed())
    except Exception as err:
        await ctx.send(":x: Import deck failed!", hidden = True)
        if (isinstance(err, binascii.Error)):
            await ctx.send("Invalid deck code!", hidden = True)
        raise err

@slash.slash(name = "update", description = "Update data from DataDragon")
async def update(ctx):
    await ctx.send("Updating data from the Data Dragon. Please stand by...")
    dd.update_data()
    await ctx.send(":white_check_mark: Update completed. You can use bot normally now.")

@bot.command(name = 'tung')
async def tung(ctx, sid = -1):
    GUILD_NBS = 808899573803909141
    id_tung = 701242005191262228
    if (ctx.guild.id is None or ctx.guild.id != GUILD_NBS):
        await ctx.send(":x: Bạn phải ở trong Discord NBS để chửi Tứng :<")
        return
    sentences = [
        "tứng ngu",
        "khỉ đầu chó",
        "không biết control",
        "thua rank Bạc",
        "36 tiếng leo rank vẫn BK4",
        "\"vực gió hú cần kỹ năng\""
    ]
    if (sid >= len(sentences)):
        await ctx.send(":x: Id sentence not found")
        return
    if (ctx.author.id == id_tung): await ctx.send("Ô, Tứng tự chửi mình à, vậy thì...")
    sens = ""
    if (sid == -1): sens = random.choice(sentences)
    else: sens = sentences[sid]
    await ctx.send(f"<@{id_tung}> {sens} :>")

bot.run(TOKEN)
