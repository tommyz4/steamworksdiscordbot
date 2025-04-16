
import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Read sensitive data from environment variables
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def steam64_to_steamid32(steam64):
    steam64 = int(steam64)
    v = 76561197960265728
    x = steam64 - v
    y = x % 2
    z = (x - y) // 2
    return f"STEAM_0:{y}:{z}"

def steam64_to_steam3id(steam64):
    steam64 = int(steam64)
    v = 76561197960265728
    account_id = steam64 - v
    return f"[U:1:{account_id}]"

def time_str_to_hours(time_str):
    hours, minutes = map(int, time_str.split(":"))
    return hours + minutes / 60

async def check_steam_mod_updates():
    async with aiohttp.ClientSession() as session:
        for guild_id, channels in data.items():
            guild = bot.get_guild(int(guild_id))
            if not guild:
                continue
            for channel_id, content in channels.items():
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    continue
                mod_list = content.get("steam_mods", [])
                for mod in mod_list[:]:
                    mod_id = mod["id"]
                    mod_name = mod["name"]
                    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
                    payload = {"itemcount": 1, "publishedfileids[0]": mod_id}
                    async with session.post(url, data=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            mod_data = result["response"]["publishedfiledetails"][0]
                            if mod_data["result"] == 1:
                                last_update = mod_data["time_updated"]
                                if "last_update" not in mod or mod["last_update"] != last_update:
                                    mod["last_update"] = last_update
                                    data[guild_id][channel_id]["steam_mods"] = mod_list
                                    save_data(data)
                                    await channel.send(f"Steam Mod **{mod_name}** ({mod_id}) updated at {datetime.fromtimestamp(last_update)}")
                            else:
                                await channel.send(f"Steam Mod **{mod_name}** ({mod_id}) has been removed from Steam Workshop! ❌")
                                mod_list.remove(mod)
                                data[guild_id][channel_id]["steam_mods"] = mod_list
                                save_data(data)

async def check_reforger_mod_updates():
    pass

async def check_game_updates():
    async with aiohttp.ClientSession() as session:
        for guild_id, channels in data.items():
            guild = bot.get_guild(int(guild_id))
            if not guild:
                continue
            for channel_id, content in channels.items():
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    continue
                game_list = content.get("games", [])
                for game in game_list[:]:
                    game_id = game["id"]
                    game_name = game["name"]
                    url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
                    async with session.get(url) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result[game_id]["success"]:
                                news_url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={game_id}&count=1"
                                async with session.get(news_url) as news_response:
                                    if news_response.status == 200:
                                        news_data = await news_response.json()
                                        if news_data["appnews"]["newsitems"]:
                                            last_update = news_data["appnews"]["newsitems"][0]["date"]
                                            if "last_update" not in game or game["last_update"] != last_update:
                                                game["last_update"] = last_update
                                                data[guild_id][channel_id]["games"] = game_list
                                                save_data(data)
                                                await channel.send(f"Game **{game_name}** ({game_id}) has new update/news at {datetime.fromtimestamp(last_update)}")
                            else:
                                await channel.send(f"Game **{game_name}** ({game_id}) is no longer available on Steam! ❌")
                                game_list.remove(game)
                                data[guild_id][channel_id]["games"] = game_list
                                save_data(data)

@tasks.loop(minutes=5)
async def update_task():
    await check_steam_mod_updates()
    await check_reforger_mod_updates()
    await check_game_updates()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not update_task.is_running():
        update_task.start()

# You can append the full set of command definitions here...
# e.g. add_channel, remove_channel, add, remove, add_game, remove_game, id64, etc.

# Run the bot using the token from .env
bot.run(DISCORD_BOT_TOKEN)
