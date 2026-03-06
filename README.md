# Rampinator

A Python desktop app that monitors multiple [Path of Exile trade](https://www.pathofexile.com/trade) live searches simultaneously and notifies you the moment new listings appear.

![Dark PoE-themed GUI with a list of active searches, status indicators, and an activity log]

## Features

- Monitor as many searches as you want at once
- Desktop notification + sound alert on new listings
- Auto-reconnects if the connection drops
- Persistent config — searches and session are saved between runs
- Dark PoE gold theme

## Requirements

- Python 3.10+
- `aiohttp` (WebSocket connections)
- `plyer` (desktop notifications, optional)

## Install & Run

```bash
pip install aiohttp plyer
python poe_live_search.py
```

## Setup

### 1. Get your POESESSID

The PoE trade live search API requires you to be logged in. Copy your session cookie:

1. Open [pathofexile.com](https://www.pathofexile.com) in your browser and log in
2. Open DevTools (`F12`) → **Application** tab → **Cookies** → `www.pathofexile.com`
3. Copy the value of `POESESSID`
4. Paste it into the **POESESSID** field in Rampinator and click **Save & Apply**

> The session cookie expires when you log out of the browser. If you get an "Auth Error", re-copy it.

### 2. Add a search

1. Go to [pathofexile.com/trade](https://www.pathofexile.com/trade) and set up your search filters
2. Copy the URL from the address bar — it looks like:
   ```
   https://www.pathofexile.com/trade/search/Standard/Yp9QVzq7IY
   ```
3. In Rampinator, click **+ Add Search**, paste the URL, give it a name, click **Add**

The search will immediately connect and show **Live** status in green. When new items are listed you'll get a desktop notification and the hit counter will increment.

## Interface

| Element | Description |
|---|---|
| POESESSID field | Your session cookie — required for auth |
| Search list | All monitored searches with live status and hit count |
| + Add Search | Paste a trade URL to start monitoring it |
| Remove Selected | Stop and remove a search |
| Open in Browser | Open the selected search on the PoE trade site |
| Toggle Enable/Disable | Pause a search without removing it |
| Activity Log | Real-time connection events and hit notifications |

### Status colors

| Color | Meaning |
|---|---|
| Green | Connected and listening |
| Orange | Connecting... |
| Red | Auth error or connection error |
| Grey | Disabled or stopped |

## Notes

- PoE's live search API requires an active logged-in session (POESESSID)
- GGG rate-limits connections — don't add hundreds of searches
- The app saves your config (including POESESSID) to `poe_live_search_config.json` in the same folder as the script
