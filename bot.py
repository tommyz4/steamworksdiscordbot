from discord.ext import commands, tasks
import aiohttp
import json
import os
from datetime import datetime
import re

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # Remove default help command

# Steam API key (replace with your own)
STEAM_API_KEY = ""

# JSON file for data storage
DATA_FILE = "data.json"

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initial data structure: {guild_id: {channel_id: {"steam_mods": [{"id": mod_id, "name": mod_name, "last_update": timestamp}], "reforger_mods": [{"id": mod_id, "name": mod_name}], "games": [{"id": game_id, "name": game_name, "last_update": timestamp}]}}}
data = load_data()

# Steam ID conversion functions
def steam64_to_steamid32(steam64):
    """Convert Steam64 ID to SteamID32 (STEAM_0:0:xxxx or STEAM_1:1:xxxx)"""
    steam64 = int(steam64)
    v = 76561197960265728  # Steam constant
    x = steam64 - v
    y = x % 2
    z = (x - y) // 2
    return f"STEAM_0:{y}:{z}"

def steam64_to_steam3id(steam64):
    """Convert Steam64 ID to Steam3ID ([U:1:xxxx])"""
    steam64 = int(steam64)
    v = 76561197960265728
    account_id = steam64 - v
    return f"[U:1:{account_id}]"

# Time string to hours conversion
def time_str_to_hours(time_str):
    hours, minutes = map(int, time_str.split(":"))
    return hours + minutes / 60

# Check Steam Workshop mods for updates
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
                    url = f"https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
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

# Placeholder for Arma Reforger Workshop mod updates
async def check_reforger_mod_updates():
    # No public API exists for Arma Reforger Workshop as of now
    # Future implementation could use an API or web scraping if permitted
    pass

# Check Steam games for updates
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

# Commands
@bot.command()
async def add_channel(ctx):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id not in data:
        data[guild_id] = {}
    if channel_id not in data[guild_id]:
        data[guild_id][channel_id] = {"steam_mods": [], "reforger_mods": [], "games": []}
        save_data(data)
        await ctx.send(f"Added {ctx.channel.mention} to mod and game tracking list.")
    else:
        await ctx.send("This channel is already in the list!")

@bot.command()
async def remove_channel(ctx):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        del data[guild_id][channel_id]
        if not data[guild_id]:
            del data[guild_id]
        save_data(data)
        await ctx.send(f"Removed {ctx.channel.mention} from mod and game tracking list.")
    else:
        await ctx.send("This channel isn’t in the list!")

@bot.command()
async def add(ctx, mod_id: str):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        if not any(mod["id"] == mod_id for mod in data[guild_id][channel_id]["steam_mods"]):
            async with aiohttp.ClientSession() as session:
                url = f"https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
                payload = {"itemcount": 1, "publishedfileids[0]": mod_id}
                async with session.post(url, data=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        mod_data = result["response"]["publishedfiledetails"][0]
                        if mod_data["result"] == 1:
                            mod_name = mod_data["title"]
                            last_update = mod_data["time_updated"]
                            data[guild_id][channel_id]["steam_mods"].append({"id": mod_id, "name": mod_name, "last_update": last_update})
                            save_data(data)
                            await ctx.send(f"Added Steam Mod **{mod_name}** ({mod_id}) to this channel’s mod list ✅")
                        else:
                            await ctx.send(f"Steam Mod {mod_id} not found on Steam Workshop!")
                    else:
                        await ctx.send("Failed to fetch Steam mod details.")
        else:
            await ctx.send("This Steam mod is already in the list!")
    else:
        await ctx.send("Add this channel first with `!add_channel`!")

@bot.command()
async def remove(ctx, mod_id: str):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        for mod in data[guild_id][channel_id]["steam_mods"]:
            if mod["id"] == mod_id:
                mod_name = mod["name"]
                data[guild_id][channel_id]["steam_mods"].remove(mod)
                save_data(data)
                await ctx.send(f"Removed Steam Mod **{mod_name}** ({mod_id}) from this channel’s mod list ❌")
                return
        await ctx.send("This Steam mod isn’t in the list!")
    else:
        await ctx.send("This channel isn’t configured!")

@bot.command()
async def add_reforger(ctx, mod_id: str, *, mod_name: str):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        if not any(mod["id"] == mod_id for mod in data[guild_id][channel_id]["reforger_mods"]):
            # No API to verify Reforger mod details, so we trust user input for now
            data[guild_id][channel_id]["reforger_mods"].append({"id": mod_id, "name": mod_name})
            save_data(data)
            await ctx.send(f"Added Arma Reforger Mod **{mod_name}** ({mod_id}) to this channel’s mod list ✅")
        else:
            await ctx.send("This Reforger mod is already in the list!")
    else:
        await ctx.send("Add this channel first with `!add_channel`!")

@bot.command()
async def remove_reforger(ctx, mod_id: str):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        for mod in data[guild_id][channel_id]["reforger_mods"]:
            if mod["id"] == mod_id:
                mod_name = mod["name"]
                data[guild_id][channel_id]["reforger_mods"].remove(mod)
                save_data(data)
                await ctx.send(f"Removed Arma Reforger Mod **{mod_name}** ({mod_id}) from this channel’s mod list ❌")
                return
        await ctx.send("This Reforger mod isn’t in the list!")
    else:
        await ctx.send("This channel isn’t configured!")

@bot.command()
async def add_game(ctx, game_id: str):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        if not any(game["id"] == game_id for game in data[guild_id][channel_id]["games"]):
            async with aiohttp.ClientSession() as session:
                url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result[game_id]["success"]:
                            game_name = result[game_id]["data"]["name"]
                            data[guild_id][channel_id]["games"].append({"id": game_id, "name": game_name})
                            save_data(data)
                            await ctx.send(f"Added Game **{game_name}** ({game_id}) to this channel’s game list ✅")
                        else:
                            await ctx.send(f"Game {game_id} not found on Steam!")
                    else:
                        await ctx.send("Failed to fetch game details from Steam.")
        else:
            await ctx.send("This game is already in the list!")
    else:
        await ctx.send("Add this channel first with `!add_channel`!")

@bot.command()
async def remove_game(ctx, game_id: str):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        for game in data[guild_id][channel_id]["games"]:
            if game["id"] == game_id:
                game_name = game["name"]
                data[guild_id][channel_id]["games"].remove(game)
                save_data(data)
                await ctx.send(f"Removed Game **{game_name}** ({game_id}) from this channel’s game list ❌")
                return
        await ctx.send("This game isn’t in the list!")
    else:
        await ctx.send("This channel isn’t configured!")

@bot.command()
async def list(ctx):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        steam_mod_list = data[guild_id][channel_id]["steam_mods"]
        reforger_mod_list = data[guild_id][channel_id]["reforger_mods"]
        game_list = data[guild_id][channel_id]["games"]
        embed = discord.Embed(title="Tracked Items", description=f"Items tracked in {ctx.channel.mention}", color=0x00ff00)
        if steam_mod_list:
            for mod in steam_mod_list:
                last_update = datetime.fromtimestamp(mod["last_update"]) if "last_update" in mod else "Not yet updated"
                embed.add_field(name=f"Steam Mod: {mod['name']} ({mod['id']})", value=f"Last update: {last_update}", inline=False)
        else:
            embed.add_field(name="Steam Mods", value="No Steam mods in this channel’s list.", inline=False)
        if reforger_mod_list:
            for mod in reforger_mod_list:
                embed.add_field(name=f"Reforger Mod: {mod['name']} ({mod['id']})", value="Manual tracking (no update info)", inline=False)
        else:
            embed.add_field(name="Reforger Mods", value="No Reforger mods in this channel’s list.", inline=False)
        if game_list:
            for game in game_list:
                last_update = datetime.fromtimestamp(game["last_update"]) if "last_update" in game else "Not yet updated"
                embed.add_field(name=f"Game: {game['name']} ({game['id']})", value=f"Last update: {last_update}", inline=False)
        else:
            embed.add_field(name="Games", value="No games in this channel’s list.", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("This channel isn’t configured!")

@bot.command()
async def list_reforger(ctx):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        reforger_mod_list = data[guild_id][channel_id]["reforger_mods"]
        if reforger_mod_list:
            embed = discord.Embed(title="Tracked Reforger Mods", description=f"Arma Reforger mods tracked in {ctx.channel.mention}", color=0x00ff00)
            for mod in reforger_mod_list:
                embed.add_field(name=f"{mod['name']} ({mod['id']})", value="Manual tracking (no update info)", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No Reforger mods in this channel’s list.")
    else:
        await ctx.send("This channel isn’t configured!")

@bot.command()
async def game_list(ctx):
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    if guild_id in data and channel_id in data[guild_id]:
        game_list = data[guild_id][channel_id]["games"]
        if game_list:
            embed = discord.Embed(title="Tracked Games", description=f"Games tracked in {ctx.channel.mention}", color=0x00ff00)
            for game in game_list:
                last_update = datetime.fromtimestamp(game["last_update"]) if "last_update" in game else "Not yet updated"
                embed.add_field(name=f"{game['name']} ({game['id']})", value=f"Last update: {last_update}", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("No games in this channel’s list.")
    else:
        await ctx.send("This channel isn’t configured!")

@bot.command()
async def id64(ctx, identifier: str):
    async with aiohttp.ClientSession() as session:
        steam_id = identifier
        if not re.match(r"^\d{17}$", identifier):
            resolve_url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={STEAM_API_KEY}&vanityurl={identifier}"
            async with session.get(resolve_url) as resolve_response:
                if resolve_response.status != 200:
                    await ctx.send("Failed to resolve username.")
                    return
                resolve_data = await resolve_response.json()
                if resolve_data["response"]["success"] == 1:
                    steam_id = resolve_data["response"]["steamid"]
                else:
                    await ctx.send(f"Username '{identifier}' not found on Steam.")
                    return

        summary_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steam_id}"
        async with session.get(summary_url) as summary_response:
            if summary_response.status != 200:
                await ctx.send("Failed to fetch Steam profile data.")
                return
            summary_data = await summary_response.json()
            player = summary_data["response"]["players"][0] if summary_data["response"]["players"] else None

        bans_url = f"http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={STEAM_API_KEY}&steamids={steam_id}"
        async with session.get(bans_url) as bans_response:
            bans_data = await bans_response.json()
            bans = bans_data["players"][0] if bans_response.status == 200 and bans_data["players"] else None

        games_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={steam_id}&include_appinfo=1"
        async with session.get(games_url) as games_response:
            if games_response.status != 200:
                await ctx.send("Failed to fetch game data from Steam.")
                return
            games_data = await games_response.json()
            games = games_data["response"].get("games", [])

        vanity_url = "Not set"
        if player and "personaname" in player:
            resolve_url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={STEAM_API_KEY}&vanityurl={player['personaname']}"
            async with session.get(resolve_url) as resolve_response:
                if resolve_response.status == 200:
                    resolve_data = await resolve_response.json()
                    if resolve_data["response"]["success"] == 1:
                        vanity_url = f"https://steamcommunity.com/id/{player['personaname']}/"
                    else:
                        profile_url = player.get("profileurl", "")
                        if "/id/" in profile_url:
                            custom_id = profile_url.split("/id/")[1].rstrip("/")
                            vanity_url = f"https://steamcommunity.com/id/{custom_id}/"

        if not player or not bans:
            await ctx.send("Invalid Steam ID or private profile.")
            return

        creation_time = datetime.fromtimestamp(player.get("timecreated", 0)) if "timecreated" in player else None
        account_age = (datetime.now() - creation_time).days // 365 if creation_time else "Unknown"
        creation_date = creation_time.strftime("%B %d, %Y") if creation_time else "Unknown"

        visibility = {1: "Private", 2: "Friends Only", 3: "Public"}
        profile_state = visibility.get(player.get("communityvisibilitystate", 1), "Unknown")

        last_seen = datetime.fromtimestamp(player["lastlogoff"]).strftime("%B %d, %Y") if "lastlogoff" in player else "Unknown"

        friend_list = "Public" if profile_state == "Public" else "Private"

        steamid32 = steam64_to_steamid32(steam_id)
        steam3id = steam64_to_steam3id(steam_id)

        ban_status = "No account bans on record"
        if bans["VACBanned"] or bans["NumberOfGameBans"] > 0:
            ban_status = f"{bans['NumberOfVACBans']} VAC ban(s), {bans['NumberOfGameBans']} game ban(s)"

        most_played = sorted(games, key=lambda x: x.get("playtime_forever", 0), reverse=True)[:3]
        most_played_str = "No games found or profile is private"
        if most_played:
            most_played_str = "\n".join(
                f"{game['name']} ({round(game['playtime_forever'] / 60, 1)} hours)"
                for game in most_played
                if "name" in game and "playtime_forever" in game
            )

        embed = discord.Embed(title="Steam Profile Data", color=0x00ff00)
        embed.add_field(name="Name", value=player['personaname'], inline=False)
        embed.add_field(name="Origin", value=player.get("loccountrycode", "Unknown"), inline=False)
        embed.add_field(
            name="Creation",
            value=f"{creation_date} ({account_age} years ago)" if creation_date != "Unknown" else "Unknown",
            inline=False
        )
        embed.add_field(name="Last Seen", value=last_seen, inline=False)
        embed.add_field(name="Configured", value="Yes" if "profileurl" in player else "No", inline=False)
        embed.add_field(name="Visibility", value=profile_state, inline=False)
        embed.add_field(name="Friend List", value=friend_list, inline=False)
        embed.add_field(name="Steam URL", value=f"https://steamcommunity.com/profiles/{steam_id}", inline=False)
        embed.add_field(name="Custom URL", value=vanity_url, inline=False)
        embed.add_field(name="Steam ID 64", value=steam_id, inline=False)
        embed.add_field(name="Steam ID 3", value=steam3id, inline=False)
        embed.add_field(name="Steam ID", value=steamid32, inline=False)
        embed.add_field(name="Bans", value=ban_status, inline=False)
        embed.add_field(name="Most Played Games", value=most_played_str, inline=False)
        embed.set_thumbnail(url=player.get("avatarfull", ""))
        await ctx.send(embed=embed)

@bot.command()
async def time(ctx, *, args):
    try:
        args = args.lower().split()
        day_str = next(arg for arg in args if arg.startswith("day_")).replace("day_", "")
        night_str = next(arg for arg in args if arg.startswith("night_")).replace("night_", "")

        real_day = time_str_to_hours(day_str)
        real_night = time_str_to_hours(night_str)

        in_game_day = 12
        in_game_night = 12

        day_multiplier = round(in_game_day / real_day, 2)
        night_multiplier = round(in_game_night / real_night, 2)

        response = (
            f"**Calculated Multipliers:**\n"
            f"ServerTimeAcceleration = `{day_multiplier}`\n"
            f"ServerNightTimeAcceleration = `{night_multiplier}`"
        )

        await ctx.send(response)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Bot Commands Help",
        description="This bot helps you track Steam Workshop mods, Arma Reforger Workshop mods, Steam games, look up Steam profiles, and calculate server time multipliers. Below is a detailed guide on how each command works. The bot automatically checks for Steam mod and game updates every 5 minutes and posts notifications in configured channels. Reforger mod updates are not yet automated due to API limitations.",
        color=0x00ff00
    )
    embed.add_field(
        name="!add_channel",
        value="**Purpose**: Configures the current Discord channel to receive updates for tracked Steam mods, Reforger mods, and games.\n"
              "**How it works**: Adds the channel to the bot’s tracking list, stored in `data.json`. You must use this command before adding mods or games.\n"
              "**Example**: `!add_channel`\n"
              "**Note**: Run this in the channel where you want updates. If the channel is already added, the bot will let you know.",
        inline=False
    )
    embed.add_field(
        name="!remove_channel",
        value="**Purpose**: Stops the current channel from receiving updates.\n"
              "**How it works**: Removes the channel from the tracking list, along with any associated mods or games.\n"
              "**Example**: `!remove_channel`\n"
              "**Note**: Only works if the channel was previously added.",
        inline=False
    )
    embed.add_field(
        name="!add <mod_id>",
        value="**Purpose**: Tracks a Steam Workshop mod for updates.\n"
              "**How it works**: Fetches the mod’s details using the Steam API and adds it to the channel’s list. Checks for updates every 5 minutes.\n"
              "**Example**: `!add 123456789`\n"
              "**Note**: Requires `!add_channel`. Find mod IDs in Steam Workshop URLs (e.g., `steamcommunity.com/sharedfiles/filedetails/?id=123456789`).",
        inline=False
    )
    embed.add_field(
        name="!remove <mod_id>",
        value="**Purpose**: Stops tracking a Steam mod.\n"
              "**How it works**: Removes the mod from the channel’s list.\n"
              "**Example**: `!remove 123456789`\n"
              "**Note**: Only works if the mod is tracked.",
        inline=False
    )
    embed.add_field(
        name="!add_reforger <mod_id> <mod_name>",
        value="**Purpose**: Tracks an Arma Reforger Workshop mod.\n"
              "**How it works**: Adds the mod ID and user-provided name to the channel’s list. No automatic updates due to lack of API.\n"
              "**Example**: `!add_reforger 5e7f8d9a-1234-5678-abcd-1234567890ab REAPER_CORE`\n"
              "**Note**: Requires `!add_channel`. Find mod IDs on reforger.armaplatform.com/workshop.",
        inline=False
    )
    embed.add_field(
        name="!remove_reforger <mod_id>",
        value="**Purpose**: Stops tracking a Reforger mod.\n"
              "**How it works**: Removes the mod from the channel’s list.\n"
              "**Example**: `!remove_reforger 5e7f8d9a-1234-5678-abcd-1234567890ab`\n"
              "**Note**: Only works if the mod is tracked.",
        inline=False
    )
    embed.add_field(
        name="!add_game <game_id>",
        value="**Purpose**: Tracks a Steam game for updates.\n"
              "**How it works**: Fetches the game’s name and adds it to the list. Checks for news every 5 minutes.\n"
              "**Example**: `!add_game 730`\n"
              "**Note**: Requires `!add_channel`. Find game IDs on SteamDB or store URLs (e.g., `store.steampowered.com/app/730`).",
        inline=False
    )
    embed.add_field(
        name="!remove_game <game_id>",
        value="**Purpose**: Stops tracking a game.\n"
              "**How it works**: Removes the game from the list.\n"
              "**Example**: `!remove_game 730`\n"
              "**Note**: Only works if the game is tracked.",
        inline=False
    )
    embed.add_field(
        name="!list",
        value="**Purpose**: Displays all tracked Steam mods, Reforger mods, and games.\n"
              "**How it works**: Shows names, IDs, and update times (where available).\n"
              "**Example**: `!list`\n"
              "**Note**: Requires channel configuration.",
        inline=False
    )
    embed.add_field(
        name="!list_reforger",
        value="**Purpose**: Displays only tracked Reforger mods.\n"
              "**How it works**: Shows names and IDs.\n"
              "**Example**: `!list_reforger`\n"
              "**Note**: Requires channel configuration.",
        inline=False
    )
    embed.add_field(
        name="!game_list",
        value="**Purpose**: Displays only tracked games.\n"
              "**How it works**: Shows names, IDs, and update times.\n"
              "**Example**: `!game_list`\n"
              "**Note**: Requires channel configuration.",
        inline=False
    )
    embed.add_field(
        name="!id64 <steam_id_or_username>",
        value="**Purpose**: Looks up a Steam profile.\n"
              "**How it works**: Displays profile details, ban status, and top games using Steam API.\n"
              "**Examples**: `!id64 76561198008001034` or `!id64 machan`\n"
              "**Note**: Private profiles may limit data.",
        inline=False
    )
    embed.add_field(
        name="!time <day_HH:MM night_HH:MM>",
        value="**Purpose**: Calculates server time acceleration multipliers.\n"
              "**How it works**: Takes real-world day/night durations and calculates multipliers for 12-hour in-game cycles.\n"
              "**Example**: `!time day_06:00 night_02:00`\n"
              "**Note**: Input must include `day_HH:MM` and `night_HH:MM`.",
        inline=False
    )
    embed.add_field(
        name="!help",
        value="**Purpose**: Shows this help message.\n"
              "**How it works**: Lists all commands and their usage.\n"
              "**Example**: `!help`\n"
              "**Note**: Use to understand bot functionality.",
        inline=False
    )
    embed.add_field(
        name="Background Info",
        value="The bot checks Steam mods and games every 5 minutes. Reforger mods are tracked manually due to no public API. Data is stored in `data.json`. Ensure valid Steam API key and Discord bot token.",
        inline=False
    )
    embed.add_field(
        name="Credits & Support",
        value="Created by **✗ | මචන්**. Support via PayPal: https://paypal.me/BooBooNexTlVl",
        inline=False
    )
    embed.set_footer(text="Bot created to help you stay updated on Steam and Reforger content!")
    await ctx.send(embed=embed)

# Run the bot put token
bot.run("")