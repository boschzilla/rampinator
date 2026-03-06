#!/usr/bin/env python3
"""
PoE Trade Live Search Monitor
Monitors multiple Path of Exile trade searches and notifies on new listings.
"""

import asyncio
import json
import os
import queue
import re
import sys
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import tkinter as tk
from tkinter import messagebox, ttk

# ---- Optional dependencies ----
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    from plyer import notification as _plyer_notify
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ---- Constants ----
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poe_live_search_config.json")
POE_TRADE_BASE = "https://www.pathofexile.com/trade/search"
POE_WS_BASE = "wss://www.pathofexile.com/api/trade/live"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
URL_PATTERN = re.compile(r"https?://www\.pathofexile\.com/trade(?:2)?/search/([^/\s]+)/([^/?\s]+)")


# ---- Data ----
@dataclass
class SearchEntry:
    name: str
    league: str
    search_id: str
    enabled: bool = True
    hit_count: int = 0
    status: str = "Idle"

    @property
    def url(self) -> str:
        return f"{POE_TRADE_BASE}/{self.league}/{self.search_id}"

    @property
    def ws_url(self) -> str:
        return f"{POE_WS_BASE}/{self.league}/{self.search_id}"

    def to_dict(self) -> dict:
        return {"name": self.name, "league": self.league, "search_id": self.search_id, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, d: dict) -> "SearchEntry":
        return cls(name=d["name"], league=d["league"], search_id=d["search_id"], enabled=d.get("enabled", True))


# ---- Background Monitor ----
class LiveSearchMonitor:
    """Runs WebSocket connections for all active searches in a background asyncio loop."""

    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.tasks: Dict[str, asyncio.Future] = {}
        self.poesessid: str = ""

    def start(self):
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _emit(self, event_type: str, **kwargs):
        self.event_queue.put({"type": event_type, **kwargs})

    def add_search(self, entry: SearchEntry):
        if not self.loop:
            return
        self.remove_search(entry.search_id)
        future = asyncio.run_coroutine_threadsafe(self._monitor(entry), self.loop)
        self.tasks[entry.search_id] = future

    def remove_search(self, search_id: str):
        if search_id in self.tasks:
            self.tasks[search_id].cancel()
            del self.tasks[search_id]

    def update_poesessid(self, poesessid: str):
        self.poesessid = poesessid

    async def _monitor(self, entry: SearchEntry):
        search_id = entry.search_id
        retry_delay = 5
        flush_handle = None  # kept in outer scope so CancelledError can cancel it

        while True:
            if not self.poesessid:
                self._emit("status", search_id=search_id, status="No POESESSID")
                await asyncio.sleep(10)
                continue

            self._emit("status", search_id=search_id, status="Connecting...")

            # Pass POESESSID as a plain Cookie header — aiohttp's CookieJar
            # won't match wss:// URLs to https:// stored cookies, so explicit
            # header injection is the only reliable way.
            conn_headers = {
                "Cookie": f"POESESSID={self.poesessid}",
                "User-Agent": USER_AGENT,
                "Origin": "https://www.pathofexile.com",
                "Referer": entry.url,
                "Accept-Language": "en-US,en;q=0.9",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }

            try:
                async with aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar()) as session:
                    async with session.ws_connect(
                        entry.ws_url,
                        headers=conn_headers,
                        timeout=aiohttp.ClientTimeout(connect=15, sock_read=None),
                        autoclose=True,
                        autoping=True,
                    ) as ws:
                        self._emit("status", search_id=search_id, status="Live")
                        retry_delay = 5

                        pending: list[str] = []

                        async def flush_pending():
                            nonlocal pending, flush_handle
                            flush_handle = None
                            # Guard: don't notify if the search was removed
                            if pending and search_id in self.tasks:
                                self._emit(
                                    "new_items",
                                    search_id=search_id,
                                    name=entry.name,
                                    count=len(pending),
                                    url=entry.url,
                                )
                            pending = []

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                except (json.JSONDecodeError, ValueError):
                                    continue

                                # New API (2024+): one JWT per new listing
                                if "result" in data:
                                    pending.append(data["result"])
                                    # Batch results that arrive within 500 ms
                                    if flush_handle:
                                        flush_handle.cancel()
                                    flush_handle = asyncio.get_event_loop().call_later(
                                        0.5, lambda: asyncio.ensure_future(flush_pending())
                                    )
                                # Old API fallback: {"new": ["id", ...]}
                                elif data.get("new"):
                                    self._emit(
                                        "new_items",
                                        search_id=search_id,
                                        name=entry.name,
                                        count=len(data["new"]),
                                        url=entry.url,
                                    )
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                self._emit("log", message=f"[{entry.name}] WS error frame: {msg.data}", tag="error")
                                break
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                self._emit("log", message=f"[{entry.name}] WS closed by server", tag="warn")
                                break

            except asyncio.CancelledError:
                if flush_handle:
                    flush_handle.cancel()
                    flush_handle = None
                self._emit("status", search_id=search_id, status="Stopped")
                return

            except aiohttp.WSServerHandshakeError as exc:
                if exc.status == 403 or (hasattr(exc, 'message') and '1008' in str(exc.message)):
                    self._emit("status", search_id=search_id, status="Auth Error")
                    self._emit("log", message=f"[{entry.name}] Auth rejected (HTTP {exc.status}) — verify your POESESSID is current.", tag="error")
                    await asyncio.sleep(max(retry_delay, 30))
                else:
                    self._emit("status", search_id=search_id, status="Disconnected")
                    self._emit("log", message=f"[{entry.name}] Handshake error {exc.status}, retrying in {retry_delay}s...", tag="warn")
                    await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

            except Exception as exc:
                self._emit("status", search_id=search_id, status="Error")
                self._emit("log", message=f"[{entry.name}] {exc}", tag="error")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)


# ---- Add Search Dialog ----
class AddSearchDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Add Live Search")
        self.geometry("520x195")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()
        self.result = None
        self._league = ""
        self._search_id = ""

        self._build()
        self.bind("<Return>", lambda _: self._on_add())
        self.bind("<Escape>", lambda _: self.destroy())

    def _build(self):
        pad = {"padx": 20, "pady": (0, 6)}

        ttk.Label(self, text="Add a PoE Trade Live Search", font=("Segoe UI", 11, "bold")).pack(pady=(14, 10))

        form = ttk.Frame(self)
        form.pack(fill=tk.X, **pad)

        ttk.Label(form, text="Trade URL:").grid(row=0, column=0, sticky="w", pady=3)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(form, textvariable=self.url_var, width=48)
        url_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=3)
        url_entry.bind("<FocusOut>", self._parse_url)
        url_entry.bind("<KeyRelease>", self._parse_url)

        ttk.Label(form, text="Name:").grid(row=1, column=0, sticky="w", pady=3)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=48).grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=3)

        self.hint_label = ttk.Label(form, text="", foreground=COLORS["muted"])
        self.hint_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 0))

        form.columnconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.pack(pady=12)
        ttk.Button(btns, text="Add", style="Accent.TButton", command=self._on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        url_entry.focus_set()

    def _parse_url(self, _=None):
        url = self.url_var.get().strip()
        m = URL_PATTERN.search(url)
        if m:
            self._league, self._search_id = m.group(1), m.group(2)
            self.hint_label.config(
                text=f"League: {self._league}   Search ID: {self._search_id}",
                foreground=COLORS["green"],
            )
            if not self.name_var.get():
                self.name_var.set(f"{self._league} Search")
        else:
            self._league = self._search_id = ""
            self.hint_label.config(
                text="Invalid URL — paste a full pathofexile.com/trade/search/... URL" if url else "",
                foreground=COLORS["red"],
            )

    def _on_add(self):
        self._parse_url()
        if not self._search_id:
            messagebox.showerror("Error", "Please paste a valid PoE trade search URL.", parent=self)
            return
        name = self.name_var.get().strip() or f"{self._league} Search"
        self.result = (name, self._league, self._search_id)
        self.destroy()


# ---- Theme ----
COLORS = {
    "bg": "#0d0d1a",
    "panel": "#12122b",
    "entry": "#1a1a3e",
    "accent": "#c8a84b",     # PoE gold
    "accent2": "#8b6914",
    "green": "#4cff91",
    "red": "#ff4c4c",
    "orange": "#ffaa33",
    "muted": "#666688",
    "fg": "#d8d4c0",
    "selected": "#1e1e4a",
}

STATUS_COLORS = {
    "Live": COLORS["green"],
    "Connecting...": COLORS["orange"],
    "Error": COLORS["red"],
    "Stopped": COLORS["muted"],
    "Idle": COLORS["muted"],
    "No POESESSID": COLORS["red"],
    "Disabled": COLORS["muted"],
}


def apply_theme(style: ttk.Style):
    c = COLORS
    style.theme_use("clam")
    style.configure(".", background=c["bg"], foreground=c["fg"], font=("Segoe UI", 9))
    style.configure("TFrame", background=c["bg"])
    style.configure("TLabel", background=c["bg"], foreground=c["fg"])
    style.configure("TLabelframe", background=c["bg"], foreground=c["fg"], bordercolor=c["entry"])
    style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent"])
    style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
    style.map("TCheckbutton", background=[("active", c["bg"])], foreground=[("active", c["accent"])])
    style.configure("TEntry", fieldbackground=c["entry"], foreground=c["fg"], insertcolor=c["fg"], bordercolor=c["entry"])
    style.configure("TButton", background=c["entry"], foreground=c["fg"], relief="flat", padding=(8, 4), borderwidth=0)
    style.map("TButton", background=[("active", c["panel"]), ("pressed", c["accent2"])])
    style.configure("Accent.TButton", background=c["accent2"], foreground="#f0e6c0", relief="flat", padding=(8, 4), borderwidth=0)
    style.map("Accent.TButton", background=[("active", c["accent"]), ("pressed", "#5a4200")])
    style.configure("Treeview", background=c["panel"], foreground=c["fg"], fieldbackground=c["panel"], rowheight=26, borderwidth=0)
    style.configure("Treeview.Heading", background=c["entry"], foreground=c["accent"], relief="flat", font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", c["selected"])], foreground=[("selected", c["accent"])])
    style.configure("TScrollbar", background=c["entry"], troughcolor=c["bg"], arrowcolor=c["muted"], relief="flat", borderwidth=0)


# ---- Main App ----
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rampinator — PoE Trade Live Search")
        self.geometry("960x620")
        self.minsize(720, 480)
        self.configure(bg=COLORS["bg"])

        style = ttk.Style(self)
        apply_theme(style)

        self.searches: Dict[str, SearchEntry] = {}
        self.event_queue: queue.Queue = queue.Queue()
        self.monitor = LiveSearchMonitor(self.event_queue)
        self.monitor.start()

        self._build_ui()
        self._load_config()
        self._poll_events()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        c = COLORS

        # ---- Top bar: POESESSID ----
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=(10, 0))

        ttk.Label(top, text="POESESSID:", foreground=c["accent"]).pack(side=tk.LEFT, padx=(0, 6))
        self.sessid_var = tk.StringVar()
        self._sessid_entry = ttk.Entry(top, textvariable=self.sessid_var, width=52, show="*")
        self._sessid_entry.pack(side=tk.LEFT, padx=(0, 4))

        self._show_var = tk.BooleanVar(value=False)
        def toggle_show():
            self._sessid_entry.config(show="" if self._show_var.get() else "*")
        ttk.Checkbutton(top, text="Show", variable=self._show_var, command=toggle_show).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top, text="Save & Apply", style="Accent.TButton", command=self._save_sessid).pack(side=tk.LEFT)
        ttk.Label(top, text="Required for live search", foreground=c["muted"]).pack(side=tk.LEFT, padx=(10, 0))

        # Notification toggles on right
        self.notify_desktop = tk.BooleanVar(value=True)
        self.notify_sound = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Sound", variable=self.notify_sound).pack(side=tk.RIGHT, padx=4)
        ttk.Checkbutton(top, text="Desktop Notify", variable=self.notify_desktop).pack(side=tk.RIGHT, padx=4)

        # ---- Searches treeview ----
        list_frame = ttk.LabelFrame(self, text="Live Searches", padding=6)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        cols = ("name", "league", "search_id", "status", "hits")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        headings = [("name", "Name", 210), ("league", "League", 130), ("search_id", "Search ID", 130), ("status", "Status", 150), ("hits", "Hits", 55)]
        for col, label, width in headings:
            self.tree.heading(col, text=label)
            anchor = "center" if col == "hits" else "w"
            self.tree.column(col, width=width, minwidth=50, anchor=anchor)

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", lambda _: self._open_in_browser())

        # ---- Action buttons ----
        btn_row = ttk.Frame(self)
        btn_row.pack(fill=tk.X, padx=12, pady=(0, 4))
        ttk.Button(btn_row, text="+ Add Search", style="Accent.TButton", command=self._add_search_dialog).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Remove Selected", command=self._remove_selected).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Open in Browser", command=self._open_in_browser).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Toggle Enable/Disable", command=self._toggle_enable).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Clear Log", command=self._clear_log).pack(side=tk.RIGHT)

        # ---- Activity log ----
        log_frame = ttk.LabelFrame(self, text="Activity Log", padding=4)
        log_frame.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.log_text = tk.Text(
            log_frame, height=7, state="disabled",
            bg=COLORS["panel"], fg=COLORS["fg"],
            font=("Consolas", 8), relief="flat", wrap="word",
            insertbackground=COLORS["fg"],
        )
        log_vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_vsb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.tag_configure("hit", foreground=COLORS["green"])
        self.log_text.tag_configure("error", foreground=COLORS["red"])
        self.log_text.tag_configure("info", foreground=COLORS["muted"])
        self.log_text.tag_configure("warn", foreground=COLORS["orange"])

        # ---- Status bar ----
        self.status_var = tk.StringVar(value="Ready — paste a POESESSID and add searches to begin.")
        tk.Label(self, textvariable=self.status_var, bg=COLORS["bg"], fg=COLORS["muted"],
                 font=("Segoe UI", 8), anchor="w").pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 4))

    # ---- Actions ----

    def _save_sessid(self):
        sid = self.sessid_var.get().strip()
        self.monitor.update_poesessid(sid)
        self._save_config()
        self._log("POESESSID saved. Reconnecting active searches...", "info")
        for entry in self.searches.values():
            if entry.enabled:
                self.monitor.add_search(entry)

    def _add_search_dialog(self):
        dlg = AddSearchDialog(self)
        self.wait_window(dlg)
        if not dlg.result:
            return
        name, league, search_id = dlg.result
        if search_id in self.searches:
            messagebox.showwarning("Duplicate", f"Search ID '{search_id}' is already being monitored.", parent=self)
            return
        entry = SearchEntry(name=name, league=league, search_id=search_id)
        self.searches[search_id] = entry
        self._tree_insert(entry)
        if entry.enabled:
            self.monitor.add_search(entry)
        self._save_config()
        self._log(f"Added search: {name} ({league}/{search_id})", "info")

    def _remove_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        sid = sel[0]
        entry = self.searches.get(sid)
        if entry and messagebox.askyesno("Remove", f"Remove '{entry.name}'?", parent=self):
            self.monitor.remove_search(sid)
            del self.searches[sid]
            self.tree.delete(sid)
            self._save_config()

    def _open_in_browser(self):
        sel = self.tree.selection()
        if sel and sel[0] in self.searches:
            webbrowser.open(self.searches[sel[0]].url)

    def _toggle_enable(self):
        sel = self.tree.selection()
        if not sel:
            return
        sid = sel[0]
        entry = self.searches[sid]
        entry.enabled = not entry.enabled
        if entry.enabled:
            self.monitor.add_search(entry)
            self._log(f"Enabled: {entry.name}", "info")
        else:
            self.monitor.remove_search(sid)
            self._tree_update(entry, "Disabled")
            self._log(f"Disabled: {entry.name}", "info")
        self._save_config()

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    # ---- Tree helpers ----

    def _tree_insert(self, entry: SearchEntry):
        self.tree.insert("", tk.END, iid=entry.search_id,
                         values=(entry.name, entry.league, entry.search_id, entry.status, entry.hit_count))

    def _tree_update(self, entry: SearchEntry, status: str = None):
        if status:
            entry.status = status
        if not self.tree.exists(entry.search_id):
            return
        self.tree.item(entry.search_id, values=(entry.name, entry.league, entry.search_id, entry.status, entry.hit_count))
        color = STATUS_COLORS.get(entry.status, COLORS["fg"])
        tag = f"s_{entry.search_id}"
        self.tree.tag_configure(tag, foreground=color)
        self.tree.item(entry.search_id, tags=(tag,))

    # ---- Log ----

    def _log(self, message: str, tag: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    # ---- Notifications ----

    def _notify(self, title: str, body: str):
        if self.notify_desktop.get() and HAS_PLYER:
            try:
                _plyer_notify.notify(title=title, message=body, app_name="Rampinator", timeout=6)
            except Exception:
                pass
        if self.notify_sound.get() and HAS_WINSOUND:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    # ---- Event pump ----

    def _poll_events(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                etype = event["type"]

                if etype == "status":
                    sid = event["search_id"]
                    if sid in self.searches:
                        self._tree_update(self.searches[sid], event["status"])

                elif etype == "new_items":
                    sid = event["search_id"]
                    if sid in self.searches:
                        entry = self.searches[sid]
                        entry.hit_count += event["count"]
                        self._tree_update(entry)
                        msg = f"NEW LISTING: {entry.name} — {event['count']} item(s)"
                        self._log(msg, "hit")
                        self._notify(f"PoE Trade: {entry.name}", f"{event['count']} new listing(s) found!")
                        self.status_var.set(f"Last hit: {entry.name} @ {datetime.now().strftime('%H:%M:%S')} — {entry.hit_count} total hits")

                elif etype == "log":
                    self._log(event["message"], event.get("tag", "info"))

        except queue.Empty:
            pass
        self.after(200, self._poll_events)

    # ---- Config ----

    def _load_config(self):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            sessid = cfg.get("poesessid", "")
            self.sessid_var.set(sessid)
            self.monitor.update_poesessid(sessid)
            for d in cfg.get("searches", []):
                try:
                    entry = SearchEntry.from_dict(d)
                    self.searches[entry.search_id] = entry
                    self._tree_insert(entry)
                    if entry.enabled:
                        self.monitor.add_search(entry)
                except (KeyError, TypeError):
                    pass
        except FileNotFoundError:
            pass
        except Exception as exc:
            self._log(f"Config load error: {exc}", "error")

    def _save_config(self):
        cfg = {
            "poesessid": self.sessid_var.get(),
            "searches": [e.to_dict() for e in self.searches.values()],
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception as exc:
            self._log(f"Config save error: {exc}", "error")

    def _on_close(self):
        self._save_config()
        self.destroy()


# ---- Entry point ----
def main():
    if not HAS_AIOHTTP:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Missing Dependency",
            "The 'aiohttp' package is required.\n\n"
            "Install it with:\n\n    pip install aiohttp plyer\n\n"
            "Then re-run the app.",
        )
        root.destroy()
        sys.exit(1)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
