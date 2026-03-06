# Rampinator — PoE Trade Live Search Monitor

Single-file Python tkinter app that monitors multiple Path of Exile trade searches via WebSocket and sends desktop/sound notifications when new listings appear.

## Run

```bash
pip install aiohttp plyer
python poe_live_search.py
```

## Files

- `poe_live_search.py` — entire application (single file)
- `poe_live_search_config.json` — auto-generated; stores POESESSID and saved searches

## Architecture

- **Main thread**: tkinter GUI (`App` class)
- **Background thread**: asyncio event loop (`LiveSearchMonitor._run_loop`)
- **Communication**: `queue.Queue` polled every 200ms via `App._poll_events` / `after()`
- Each search runs its own `_monitor` coroutine as an `asyncio.Task` in the background loop
- Auto-reconnects with exponential backoff (5s → 60s max)

## Key classes

| Class | Role |
|---|---|
| `SearchEntry` | Dataclass holding name, league, search_id, status, hit_count |
| `LiveSearchMonitor` | Owns the asyncio loop + all WS tasks; emits events via queue |
| `App` | tkinter root; builds UI, polls event queue, handles config |
| `AddSearchDialog` | Toplevel dialog; parses pasted trade URL into league + search_id |

## PoE Trade WebSocket API

- **URL**: `wss://www.pathofexile.com/api/trade/live/{league}/{search_id}`
- **Auth**: `Cookie: POESESSID=<value>` sent as explicit request header (not via cookie jar — aiohttp's jar won't match wss:// to https:// stored cookies)
- **Required headers**: `Origin`, `Referer` (must be the trade page URL), `User-Agent`
- **Message format** (current as of 2024+): `{"result": "JWT_TOKEN"}` — one message per new listing
- **Old format fallback**: `{"new": ["id1", "id2", ...]}` — still handled
- **Auth confirmation**: server sends `{"auth": true}` on successful connect
- Connection uses `aiohttp.DummyCookieJar()` to prevent cookie jar interference

## Getting POESESSID

Open browser DevTools on pathofexile.com → Application → Cookies → `www.pathofexile.com` → copy `POESESSID` value. Expires with the browser session.

## Config format

```json
{
  "poesessid": "abc123...",
  "searches": [
    {"name": "My Search", "league": "Standard", "search_id": "Yp9QVzq7IY", "enabled": true}
  ]
}
```

## Dependencies

| Package | Required | Purpose |
|---|---|---|
| `aiohttp` | Yes | WebSocket connections |
| `plyer` | No | Desktop notifications |
| `winsound` | No (Windows built-in) | Sound alert |
| `tkinter` | Yes (stdlib) | GUI |
