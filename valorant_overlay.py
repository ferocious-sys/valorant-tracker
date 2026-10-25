"""Small Windows desktop overlay for ranks of explicitly entered players."""

import argparse
import ctypes
import ctypes.wintypes
import os
import queue
import sys
import threading

from valorant_tracker import Client, TrackerError, clean, lookup


HOTKEY_ID = 0x5654
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
VK_F8 = 0x77
MOD_NOREPEAT = 0x4000


def rank_entry(player, client):
    """Return the public data needed for one manually selected player card."""
    args = argparse.Namespace(command="rank", player=player, region=None, platform="pc")
    data = lookup(args, client)
    current = data["rank"].get("current") or {}
    tier = current.get("tier") or {}
    return {
        "name": clean(f'{data["account"]["name"]}#{data["account"]["tag"]}'),
        "rank": clean(tier.get("name") or "Unrated"),
        "rr": current.get("rr"),
    }


def run(players):
    if sys.platform != "win32":
        raise TrackerError("The desktop overlay currently supports Windows only.")
    try:
        import tkinter as tk
    except ImportError:
        raise TrackerError("This Python installation needs Tkinter to show the overlay.") from None

    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, VK_F8):
        raise TrackerError("F8 is already used by another app. Close it and try again.")

    root = None
    try:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            raise TrackerError("Could not open the desktop overlay. Start it in a Windows desktop session.") from exc
        root.title("VALORANT Tracker overlay")
        root.configure(bg="#111626")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.94)
        root.resizable(False, False)

        shell = tk.Frame(root, bg="#111626", highlightbackground="#605978", highlightthickness=1)
        shell.pack(fill="both", expand=True)
        bar = tk.Frame(shell, bg="#242a43", cursor="fleur")
        bar.pack(fill="x")
        tk.Label(bar, text="V  /  PLAYER RANKS", bg="#242a43", fg="#e1d8ff",
                 font=("Segoe UI", 10, "bold"), padx=14, pady=9).pack(side="left")
        status = tk.Label(bar, text="F8  HIDE / SHOW", bg="#242a43", fg="#aeb5ce",
                          font=("Segoe UI", 8), padx=12)
        status.pack(side="right")
        cards = tk.Frame(shell, bg="#111626", padx=12, pady=12)
        cards.pack(fill="x")
        labels = []
        for index, player in enumerate(players):
            card = tk.Frame(cards, bg="#1c2339", padx=14, pady=11,
                            highlightbackground="#3f4560", highlightthickness=1)
            card.grid(row=0, column=index, padx=5, sticky="nsew")
            cards.grid_columnconfigure(index, weight=1)
            rank = tk.Label(card, text="LOADING…", bg="#1c2339", fg="#c9bbff",
                            font=("Segoe UI", 12, "bold"), width=18)
            rank.pack()
            name = tk.Label(card, text="#".join(player), bg="#1c2339", fg="#f3f4ff",
                            font=("Segoe UI", 10), pady=5)
            name.pack()
            labels.append((rank, name))

        buttons = tk.Frame(shell, bg="#111626", padx=16, pady=7)
        buttons.pack(fill="x")
        tk.Label(buttons, text="Entered players only · F8 toggles overlay",
                 bg="#111626", fg="#8f9ab3", font=("Segoe UI", 8)).pack(side="left")

        results = queue.Queue()
        refreshing = False

        def refresh():
            nonlocal refreshing
            if refreshing:
                return
            refreshing = True
            refresh_button.configure(state="disabled")
            status.configure(text="UPDATING…")
            for rank_label, _ in labels:
                rank_label.configure(text="LOADING…")

            def fetch():
                try:
                    client = Client(os.environ.get("HENRIK_API_KEY"))
                except TrackerError as exc:
                    results.put((None, str(exc)))
                    return
                for index, player in enumerate(players):
                    try:
                        results.put((index, rank_entry(player, client)))
                    except (TrackerError, KeyError, TypeError, ValueError) as exc:
                        results.put((index, {"name": "#".join(player), "rank": "Unavailable", "rr": None}))
                results.put((None, None))

            threading.Thread(target=fetch, daemon=True).start()

        def close():
            root.destroy()

        refresh_button = tk.Button(buttons, text="Refresh", command=refresh, bg="#c9bbff", fg="#15172a",
                                   activebackground="#e2d9ff", relief="flat", padx=12, pady=5)
        refresh_button.pack(side="right", padx=(8, 0))
        tk.Button(buttons, text="Close", command=close, bg="#30364d", fg="#f3f4ff",
                  activebackground="#404762", relief="flat", padx=12, pady=5).pack(side="right")

        drag = {}

        def start_drag(event):
            drag["x"], drag["y"] = event.x_root - root.winfo_x(), event.y_root - root.winfo_y()

        def move_drag(event):
            root.geometry(f'+{event.x_root - drag["x"]}+{event.y_root - drag["y"]}')

        for widget in (bar, bar.winfo_children()[0], status):
            widget.bind("<ButtonPress-1>", start_drag)
            widget.bind("<B1-Motion>", move_drag)

        root.update_idletasks()
        width = root.winfo_reqwidth()
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        root.geometry(f"+{x}+36")

        def pump():
            nonlocal refreshing
            message = ctypes.wintypes.MSG()
            while user32.PeekMessageW(ctypes.byref(message), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
                if message.wParam == HOTKEY_ID:
                    if root.state() == "withdrawn":
                        root.deiconify()
                        root.attributes("-topmost", True)
                    else:
                        root.withdraw()
            while True:
                try:
                    index, value = results.get_nowait()
                except queue.Empty:
                    break
                if index is None:
                    if value:
                        for rank_label, _ in labels:
                            rank_label.configure(text="KEY REQUIRED")
                        status.configure(text="CHECK API KEY")
                        print(f"Overlay: {value}", file=sys.stderr)
                    else:
                        status.configure(text="F8  HIDE / SHOW")
                    refreshing = False
                    refresh_button.configure(state="normal")
                else:
                    rank = value["rank"]
                    if value["rr"] is not None:
                        rank += f'  ·  {value["rr"]} RR'
                    labels[index][0].configure(text=rank)
                    labels[index][1].configure(text=value["name"])
            root.after(100, pump)

        pump()
        refresh()
        print("Overlay open. Press F8 to hide/show; click Refresh for current ranks; Close to exit.")
        root.mainloop()
        return 0
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)


if __name__ == "__main__":
    print("Start with: python valorant_tracker.py overlay \"Player#TAG\"")
