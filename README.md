# 🛠 Discord Steam Tracker Bot

This bot is built using **discord.py** (`discord.ext.commands`) and helps Discord communities track and get alerts for:

- ✅ Steam Workshop Mods
- ✅ Arma Reforger Mods (manual tracking)
- ✅ Steam Games
- ✅ Steam Profile lookups
- ✅ Server time acceleration calculations (for survival games like DayZ)

---

## 📁 Data Structure

Data is stored in a `data.json` file per guild and channel:

```json
{
  "guild_id": {
    "channel_id": {
      "steam_mods": [{"id": "123", "name": "ModName", "last_update": 1710000000}],
      "reforger_mods": [{"id": "mod-uuid", "name": "ReforgerMod"}],
      "games": [{"id": "730", "name": "CS:GO", "last_update": 1710000000}]
    }
  }
}
```

---

## 🔁 Automated Tasks (Runs Every 5 Minutes)

- **Steam Mods**: Checks for mod updates via Steam API.
- **Steam Games**: Checks for latest news to detect updates.
- **Reforger Mods**: Placeholder for future API support.

Alerts are sent to configured channels when updates are detected.

---

## 💬 Commands

### Configuration
- `!add_channel` — Enables tracking in the current channel.
- `!remove_channel` — Disables tracking for the current channel.

### Steam Mods
- `!add <mod_id>` — Add Steam Workshop mod.
- `!remove <mod_id>` — Remove tracked mod.
- `!list` — List all tracked mods/games in the channel.

### Arma Reforger Mods
- `!add_reforger <mod_id> <mod_name>` — Add a Reforger mod manually.
- `!remove_reforger <mod_id>` — Remove a Reforger mod.
- `!list_reforger` — List only Reforger mods.

### Steam Games
- `!add_game <app_id>` — Track a game by Steam App ID.
- `!remove_game <app_id>` — Stop tracking a game.
- `!game_list` — List tracked games.

### Steam Profile Lookup
- `!id64 <steam_id or username>` — Fetch profile info, bans, and most played games.

### Server Time Multipliers
- `!time day_HH:MM night_HH:MM` — Calculates acceleration multipliers for in-game cycles.

### Help
- `!help` — Show all command documentation.

---

## 🔗 External APIs Used

- `ISteamRemoteStorage/GetPublishedFileDetails`
- `ISteamNews/GetNewsForApp`
- `ISteamUser/GetPlayerSummaries`, `GetPlayerBans`
- `IPlayerService/GetOwnedGames`
- `ISteamUser/ResolveVanityURL`
- `store.steampowered.com/api/appdetails`

---

## 🔐 Requirements

1. Install dependencies:
```bash
pip install discord.py aiohttp python-dotenv
```

2. Create a `.env` file in your project directory with the following content:

```env
STEAM_API_KEY=your_steam_api_key_here
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

3. Run the bot:
```bash
python bot.py
```

---

## ⚡ Summary

This bot is ideal for communities running survival or mod-heavy games like DayZ or Arma. It keeps users informed of mod/game updates and can analyze player Steam profiles.
