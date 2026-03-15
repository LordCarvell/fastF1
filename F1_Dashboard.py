# SECTION 1 - IMPORTS #

import os
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading

# SECTION 2 - FAST F1 #

try:
    import fastf1
    import fastf1.plotting
    FASTF1_AVAILABLE = True
except ImportError:
    FASTF1_AVAILABLE = False
if not FASTF1_AVAILABLE:
    print("FASTF1 not available")

# SECTION 3 - COLOURS #

BG_DARK      = "#0a0a0f"
BG_PANEL     = "#12121a"
BG_CARD      = "#1a1a26"
ACCENT_RED   = "#e8002d"
ACCENT_GOLD  = "#ffd700"
TEXT_PRIMARY = "#ffffff"
TEXT_DIM     = "#8888aa"
BORDER       = "#2a2a3a"

# Base team colours (2018-2025)
_TEAM_COLOURS_BASE = {
    "Red Bull Racing":    "#3671C6",
    "Ferrari":            "#E8002D",
    "Mercedes":           "#27F4D2",
    "McLaren":            "#FF8000",
    "Aston Martin":       "#229971",
    "Alpine":             "#FF87BC",
    "Williams":           "#64C4FF",
    "RB":                 "#6692FF",
    "Haas F1 Team":       "#B6BABD",
    "Kick Sauber":        "#52E252",
}

# 2026 overrides — Kick Sauber becomes Audi, Cadillac joins
_TEAM_COLOURS_2026 = {
    **_TEAM_COLOURS_BASE,
    "Audi":      "#C0001B",   # Audi red
    "Cadillac":  "#C8A84B",   # Cadillac gold
}
_TEAM_COLOURS_2026.pop("Kick Sauber", None)

def get_team_colours(year: int) -> dict:
    """Return the correct team colour map for the given season."""
    return _TEAM_COLOURS_2026 if year >= 2026 else _TEAM_COLOURS_BASE

# Sessions per weekend format
STANDARD_SESSIONS = ["FP1", "FP2", "FP3", "Q", "R"]
SPRINT_SESSIONS   = ["FP1", "SQ", "S", "Q", "R"]

SESSION_LABELS = {
    "FP1": "FP1 — Practice 1",
    "FP2": "FP2 — Practice 2",
    "FP3": "FP3 — Practice 3",
    "Q":   "Q   — Qualifying",
    "R":   "R   — Race",
    "SQ":  "SQ  — Sprint Qualifying",
    "S":   "S   — Sprint Race",
}

# SECTION 4 - UTILITY #

def lap_time_str(td):
    """Convert timedelta to m:ss.mmm string."""
    if td is None:
        return "N/A"
    total = td.total_seconds()
    m = int(total // 60)
    s = total % 60
    return f"{m}:{s:06.3f}"


def is_sprint_weekend(event):
    """Return True if the event has a Sprint session."""
    for col in ["Session3", "Session4", "Session5"]:
        val = str(event.get(col, "")).strip().lower()
        if val in ("sprint", "sprint shootout", "sprint qualifying"):
            return True
    return False


# SECTION 5 - DASHBOARD #

class F1Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("F1 Dashboard")
        self.geometry("1280x800")
        self.minsize(1000, 680)
        self.configure(bg=BG_DARK)

        self._apply_style()

        # State
        self.session         = None
        self.session_loaded  = False
        self.selected_drivers = []
        self._schedule       = {}   # round_number -> event row
        self._round_labels   = []   # ordered display strings
        self._label_to_round = {}   # label -> round number
        self._current_round  = None

        # Layout
        self._build_sidebar()
        self._build_main()
        self._show_welcome()

        # Kick off schedule fetch for default year
        if FASTF1_AVAILABLE:
            self._fetch_schedule()

    # SECTION 5.1 - STYLE

    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".",
            background=BG_DARK, foreground=TEXT_PRIMARY,
            fieldbackground=BG_CARD, troughcolor=BG_PANEL,
            bordercolor=BORDER, selectbackground=ACCENT_RED,
            selectforeground=TEXT_PRIMARY, font=("Helvetica", 11),
        )
        style.configure("TLabel",     background=BG_DARK,  foreground=TEXT_PRIMARY)
        style.configure("TFrame",     background=BG_DARK)
        style.configure("TCombobox",  fieldbackground=BG_CARD, foreground=TEXT_PRIMARY)
        style.configure("TScrollbar", background=BG_PANEL, troughcolor=BG_DARK)
        style.configure("TNotebook",  background=BG_PANEL, tabmargins=[2, 2, 0, 0])
        style.configure("TNotebook.Tab",
            background=BG_CARD, foreground=TEXT_DIM, padding=[14, 6],
            font=("Helvetica", 10, "bold"),
        )
        style.map("TNotebook.Tab",
            background=[("selected", BG_DARK)],
            foreground=[("selected", ACCENT_RED)],
        )
        style.configure("Red.TButton",
            background=ACCENT_RED, foreground=TEXT_PRIMARY,
            font=("Helvetica", 11, "bold"), padding=[10, 6], relief="flat",
        )
        style.map("Red.TButton",
            background=[("active", "#ff1a47"), ("pressed", "#b00022")],
        )
        style.configure("Dim.TLabel",   background=BG_DARK, foreground=TEXT_DIM,     font=("Helvetica", 10))
        style.configure("Title.TLabel", background=BG_DARK, foreground=TEXT_PRIMARY, font=("Helvetica", 13, "bold"))
        style.configure("Card.TFrame",  background=BG_CARD, relief="flat")

    # SECTION 5.2 - SIDEBAR

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=BG_PANEL, width=260)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo
        logo_frame = tk.Frame(sidebar, bg=ACCENT_RED, height=70)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="F1", bg=ACCENT_RED, fg="white",
                 font=("Helvetica", 28, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(logo_frame, text="Dashboard", bg=ACCENT_RED, fg="white",
                 font=("Helvetica", 12)).pack(side="left")

        pad = dict(padx=16, pady=6)

        om_cfg = dict(
            bg=BG_CARD, fg=TEXT_PRIMARY, activebackground=ACCENT_RED,
            activeforeground=TEXT_PRIMARY, highlightthickness=0,
            relief="flat", font=("Helvetica", 11), anchor="w",
            indicatoron=True, bd=0,
        )
        menu_cfg = dict(
            bg=BG_CARD, fg=TEXT_PRIMARY, activebackground=ACCENT_RED,
            activeforeground=TEXT_PRIMARY, relief="flat",
            font=("Helvetica", 11), bd=0, tearoff=0,
        )

        # Season
        tk.Label(sidebar, text="SEASON", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(18, 2))
        self.year_var = tk.StringVar(value="2026")
        year_menu = tk.OptionMenu(sidebar, self.year_var, *[str(y) for y in range(2018, 2027)])
        year_menu.config(width=22, **om_cfg)
        year_menu["menu"].config(**menu_cfg)
        year_menu.pack(**pad)
        self.year_var.trace_add("write", lambda *_: self._fetch_schedule())

        # Round — populated from schedule
        tk.Label(sidebar, text="ROUND", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        self.round_label_var = tk.StringVar(value="Fetching schedule…")
        self.round_menu = tk.OptionMenu(sidebar, self.round_label_var, "Fetching schedule…")
        self.round_menu.config(width=22, state="disabled", **om_cfg)
        self.round_menu["menu"].config(**menu_cfg)
        self.round_menu.pack(**pad)
        self.round_label_var.trace_add("write", lambda *_: self._on_round_selected())

        # Session — filtered per weekend type
        tk.Label(sidebar, text="SESSION", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(10, 2))
        self.session_label_var = tk.StringVar(value="—")
        self.session_menu = tk.OptionMenu(sidebar, self.session_label_var, "—")
        self.session_menu.config(width=22, state="disabled", **om_cfg)
        self.session_menu["menu"].config(**menu_cfg)
        self.session_menu.pack(**pad)

        # Load button
        tk.Frame(sidebar, bg=BG_PANEL, height=10).pack()
        ttk.Button(sidebar, text="LOAD SESSION", style="Red.TButton",
                   command=self._load_session).pack(padx=16, fill="x")

        # Status
        msg = "Fetching schedule…" if FASTF1_AVAILABLE else "FastF1 not installed"
        self.status_var = tk.StringVar(value=msg)
        tk.Label(sidebar, textvariable=self.status_var, bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Helvetica", 9), wraplength=220).pack(padx=16, pady=8, anchor="w")

        # Separator
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=16, pady=10)

        # Driver selector
        tk.Label(sidebar, text="COMPARE DRIVERS", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=16, pady=(0, 4))

        list_frame = tk.Frame(sidebar, bg=BG_PANEL)
        list_frame.pack(fill="x", padx=16)
        scrollbar = tk.Scrollbar(list_frame, bg=BG_PANEL)
        scrollbar.pack(side="right", fill="y")
        self.driver_listbox = tk.Listbox(
            list_frame, selectmode="multiple", height=10,
            bg=BG_CARD, fg=TEXT_PRIMARY, selectbackground=ACCENT_RED,
            activestyle="none", borderwidth=0, highlightthickness=0,
            font=("Helvetica", 11), yscrollcommand=scrollbar.set,
        )
        self.driver_listbox.pack(fill="x")
        scrollbar.config(command=self.driver_listbox.yview)

        ttk.Button(sidebar, text="PLOT SELECTED", style="Red.TButton",
                   command=self._plot_selected).pack(padx=16, fill="x", pady=(6, 0))

        # Footer
        tk.Frame(sidebar, bg=BG_PANEL).pack(expand=True)
        tk.Label(sidebar, text="fastf1 + matplotlib", bg=BG_PANEL, fg=TEXT_DIM,
                 font=("Helvetica", 8)).pack(pady=8)

    # SECTION 5.3 - SCHEDULE FETCHING

    def _fetch_schedule(self):
        if not FASTF1_AVAILABLE:
            return
        year = int(self.year_var.get())
        self.round_menu.config(state="disabled")
        self.session_menu.config(state="disabled")
        self.round_label_var.set("Loading schedule…")
        self.session_label_var.set("—")
        self.status_var.set(f"Fetching {year} schedule…")

        def _load():
            try:
                os.makedirs("f1_cache", exist_ok=True)
                fastf1.Cache.enable_cache("f1_cache")
                schedule = fastf1.get_event_schedule(year, include_testing=False)
                self.after(0, lambda: self._on_schedule_loaded(schedule))
            except Exception as e:
                self.after(0, lambda: self._on_schedule_error(str(e)))

        threading.Thread(target=_load, daemon=True).start()

    def _on_schedule_loaded(self, schedule):
        import datetime
        self._schedule = {}
        self._round_labels = []
        self._label_to_round = {}

        year     = int(self.year_var.get())
        today    = datetime.date.today()
        is_current_year = (year == today.year)

        for _, event in schedule.iterrows():
            rnd  = int(event["RoundNumber"])
            name = event["EventName"]

            # For the current season, skip rounds whose race date is in the future
            if is_current_year:
                race_date = event.get("EventDate")
                try:
                    if hasattr(race_date, "date"):
                        race_date = race_date.date()
                    elif isinstance(race_date, str):
                        race_date = datetime.date.fromisoformat(race_date[:10])
                    if race_date > today:
                        continue   # not yet raced
                except Exception:
                    pass  # if date unreadable, include it anyway

            label = f"R{rnd:02d} — {name}"
            self._schedule[rnd] = event
            self._round_labels.append(label)
            self._label_to_round[label] = rnd

        # Repopulate the round OptionMenu
        menu = self.round_menu["menu"]
        menu.delete(0, "end")
        for lbl in self._round_labels:
            menu.add_command(label=lbl, command=lambda l=lbl: self.round_label_var.set(l))

        if self._round_labels:
            self.round_menu.config(state="normal")
            # Temporarily pause trace to avoid double-fire, set directly
            self.round_label_var.set(self._round_labels[-1])
        else:
            self.round_label_var.set("No completed rounds yet")
            self.status_var.set(f"No completed rounds in {year} yet")
            return

        suffix = " (completed rounds only)" if is_current_year else ""
        self.status_var.set(f"✓ {year} — {len(self._round_labels)} rounds{suffix}")

    def _on_schedule_error(self, msg):
        self.status_var.set("Could not load schedule")
        self.round_label_var.set("Error — check connection")

    def _on_round_selected(self):
        label = self.round_label_var.get()
        rnd   = self._label_to_round.get(label)
        if rnd is None:
            return

        self._current_round = rnd
        event  = self._schedule[rnd]
        sprint = is_sprint_weekend(event)

        keys   = SPRINT_SESSIONS if sprint else STANDARD_SESSIONS
        labels = [SESSION_LABELS[k] for k in keys]

        menu = self.session_menu["menu"]
        menu.delete(0, "end")
        for lbl in labels:
            menu.add_command(label=lbl, command=lambda l=lbl: self.session_label_var.set(l))
        self.session_menu.config(state="normal")
        self.session_label_var.set(SESSION_LABELS["R"])   # default to Race

        badge = "🏁 Sprint weekend" if sprint else "Standard weekend"
        self.status_var.set(f"{event['EventName']} — {badge}")

    def _get_session_key(self):
        """Convert displayed label back to short key e.g. 'FP1'."""
        label = self.session_label_var.get()
        for k, v in SESSION_LABELS.items():
            if v == label:
                return k
        return label

    # SECTION 5.4 - MAIN AREA

    def _build_main(self):
        self.main = tk.Frame(self, bg=BG_DARK)
        self.main.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(self.main)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_overview  = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_laps      = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_telemetry = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_results   = tk.Frame(self.notebook, bg=BG_DARK)

        self.notebook.add(self.tab_overview,  text="  Overview  ")
        self.notebook.add(self.tab_laps,      text="  Lap Times  ")
        self.notebook.add(self.tab_telemetry, text="  Telemetry  ")
        self.notebook.add(self.tab_results,   text="  Results  ")

    # SECTION 5.5 - WELCOME SCREEN

    def _show_welcome(self):
        for tab in [self.tab_overview, self.tab_laps, self.tab_telemetry, self.tab_results]:
            for w in tab.winfo_children():
                w.destroy()

        frame = tk.Frame(self.tab_overview, bg=BG_DARK)
        frame.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(frame, text="🏎", font=("Helvetica", 48), bg=BG_DARK).pack()
        tk.Label(frame, text="F1 DASHBOARD", bg=BG_DARK, fg=TEXT_PRIMARY,
                 font=("Helvetica", 26, "bold")).pack(pady=(8, 4))
        tk.Label(frame, text="Select a season, round and session type,\nthen click LOAD SESSION to begin.",
                 bg=BG_DARK, fg=TEXT_DIM, font=("Helvetica", 12)).pack()

        if not FASTF1_AVAILABLE:
            tk.Label(frame,
                text="⚠  FastF1 not installed.\nRun:  pip install fastf1 matplotlib",
                bg="#2a0a0a", fg="#ff6666", font=("Helvetica", 11),
                pady=10, padx=16, relief="flat",
            ).pack(pady=20)

    # SECTION 5.6 - LOAD SESSION

    def _load_session(self):
        if not FASTF1_AVAILABLE:
            messagebox.showerror("Missing dependency",
                "FastF1 is not installed.\n\nRun:\n  pip install fastf1 matplotlib")
            return
        if not self._current_round:
            messagebox.showinfo("No round selected", "Wait for the schedule to load, then pick a round.")
            return

        year   = int(self.year_var.get())
        round_ = self._current_round
        ses    = self._get_session_key()

        self.status_var.set("Loading session data… please wait")
        self.update()

        def _load():
            try:
                os.makedirs("f1_cache", exist_ok=True)
                fastf1.Cache.enable_cache("f1_cache")
                session = fastf1.get_session(year, round_, ses)
                session.load()
                self.session = session
                self.session_loaded = True
                self.after(0, self._on_session_loaded)
            except Exception as e:
                self.after(0, lambda: self._on_load_error(str(e)))

        threading.Thread(target=_load, daemon=True).start()

    def _on_load_error(self, msg):
        self.status_var.set("Error loading session")
        messagebox.showerror("Load failed", msg)

    def _on_session_loaded(self):
        s = self.session
        self.status_var.set(f"✓ {s.event['EventName']} {s.event.year} — {s.name}")
        self.driver_listbox.delete(0, "end")
        for d in sorted(s.laps["Driver"].unique()):
            self.driver_listbox.insert("end", d)
        self._build_overview()
        self._build_results_table()

    # SECTION 5.7 - OVERVIEW TAB

    def _build_overview(self):
        for w in self.tab_overview.winfo_children():
            w.destroy()
        s = self.session

        hdr = tk.Frame(self.tab_overview, bg=ACCENT_RED, height=56)
        hdr.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(hdr, text=f"  {s.event['EventName'].upper()}",
                 bg=ACCENT_RED, fg="white", font=("Helvetica", 16, "bold")).pack(side="left")
        tk.Label(hdr, text=f"{s.event.year}  |  {s.name}  |  {s.event['Location']}  ",
                 bg=ACCENT_RED, fg="white", font=("Helvetica", 11)).pack(side="right")

        stats_row = tk.Frame(self.tab_overview, bg=BG_DARK)
        stats_row.pack(fill="x", padx=10, pady=10)

        laps           = s.laps
        fastest        = laps.pick_fastest()
        fastest_time   = lap_time_str(fastest["LapTime"]) if fastest is not None else "N/A"
        fastest_driver = fastest["Driver"]               if fastest is not None else "N/A"

        for label, val in [
            ("Fastest Lap", fastest_time),
            ("By",          fastest_driver),
            ("Drivers",     str(len(laps["Driver"].unique()))),
            ("Total Laps",  str(len(laps))),
        ]:
            card = tk.Frame(stats_row, bg=BG_CARD, padx=20, pady=14)
            card.pack(side="left", fill="x", expand=True, padx=5)
            tk.Label(card, text=label, bg=BG_CARD, fg=TEXT_DIM,     font=("Helvetica", 9, "bold")).pack()
            tk.Label(card, text=val,   bg=BG_CARD, fg=TEXT_PRIMARY, font=("Helvetica", 18, "bold")).pack()

        fig = Figure(figsize=(8, 3.8), facecolor=BG_DARK)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(BG_PANEL)

        top_drivers = (
            laps.groupby("Driver")["LapTime"]
            .median().dropna().sort_values().head(10).index.tolist()
        )
        colours, boxes_data = [], []
        for drv in top_drivers:
            drv_laps = laps.pick_driver(drv).pick_quicklaps()
            times    = drv_laps["LapTime"].dt.total_seconds().dropna()
            boxes_data.append(times.values if len(times) > 0 else [0])
            team = laps[laps["Driver"] == drv]["Team"].iloc[0] if len(laps[laps["Driver"] == drv]) > 0 else ""
            colours.append(get_team_colours(int(self.year_var.get())).get(team, ACCENT_GOLD))

        bp = ax.boxplot(boxes_data, patch_artist=True, labels=top_drivers,
                        medianprops=dict(color="white", linewidth=2),
                        whiskerprops=dict(color=TEXT_DIM),
                        capprops=dict(color=TEXT_DIM),
                        flierprops=dict(markerfacecolor=TEXT_DIM, marker="o", markersize=3))
        for patch, colour in zip(bp["boxes"], colours):
            patch.set_facecolor(colour)
            patch.set_alpha(0.85)

        ax.set_title("Lap Time Distribution — Top 10", color=TEXT_PRIMARY,
                     fontsize=12, fontweight="bold", pad=10)
        ax.set_ylabel("Lap Time (s)", color=TEXT_DIM, fontsize=9)
        ax.tick_params(colors=TEXT_DIM)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.set_facecolor(BG_PANEL)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.tab_overview)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))
        canvas.draw()

    # SECTION 5.8 - RESULTS TABLE

    def _build_results_table(self):
        for w in self.tab_results.winfo_children():
            w.destroy()
        s = self.session

        cols   = ("Pos", "Driver", "Team", "Best Lap", "Gap", "Status")
        tree   = ttk.Treeview(self.tab_results, columns=cols, show="headings", height=22)
        widths = [45, 70, 170, 105, 90, 90]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        tree.tag_configure("odd",    background=BG_CARD,    foreground=TEXT_PRIMARY)
        tree.tag_configure("even",   background=BG_PANEL,   foreground=TEXT_PRIMARY)
        tree.tag_configure("dnf",    background="#1a0a0a",   foreground="#cc4444")
        tree.tag_configure("dns",    background="#0f0f1a",   foreground="#666688")

        laps = s.laps

        # All drivers who appear in laps data
        all_drivers = laps["Driver"].unique()

        # Build rows: drivers with lap times (finishers + partial DNFs)
        driver_best = (
            laps.groupby("Driver")["LapTime"]
            .min().dropna().sort_values().reset_index()
        )
        classified_drivers = set(driver_best["Driver"].tolist())
        leader_time = driver_best.iloc[0]["LapTime"] if len(driver_best) > 0 else None

        rows = []
        pos  = 1
        for _, row in driver_best.iterrows():
            drv    = row["Driver"]
            team   = laps[laps["Driver"] == drv]["Team"].iloc[0] if len(laps[laps["Driver"] == drv]) > 0 else ""
            best   = lap_time_str(row["LapTime"])
            gap    = "LEADER" if pos == 1 else f"+{(row['LapTime'] - leader_time).total_seconds():.3f}"
            # Classify as DNF if they set laps but finished significantly fewer than the leader
            max_lap    = laps["LapNumber"].max()
            driver_max = laps[laps["Driver"] == drv]["LapNumber"].max()
            finished   = driver_max >= (max_lap - 3)   # within 3 laps of the end = classified
            status     = "Classified" if finished else "DNF"
            tag        = ("odd" if pos % 2 == 1 else "even") if finished else "dnf"
            rows.append((pos, drv, team, best, gap, status, tag))
            pos += 1

        # DNS — drivers in laps data but with zero recorded lap times
        for drv in all_drivers:
            if drv not in classified_drivers:
                team = laps[laps["Driver"] == drv]["Team"].iloc[0] if len(laps[laps["Driver"] == drv]) > 0 else ""
                rows.append((pos, drv, team, "—", "—", "DNS", "dns"))
                pos += 1

        for row in rows:
            tree.insert("", "end", values=row[:6], tags=(row[6],))

        sb = ttk.Scrollbar(self.tab_results, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

    # SECTION 5.9 - PLOT SELECTED

    def _plot_selected(self):
        if not self.session_loaded:
            messagebox.showinfo("No session", "Load a session first.")
            return
        idxs = self.driver_listbox.curselection()
        if not idxs:
            messagebox.showinfo("No drivers", "Select at least one driver from the list.")
            return
        drivers = [self.driver_listbox.get(i) for i in idxs]
        self._build_lap_times_chart(drivers)
        self._build_telemetry_chart(drivers)
        self.notebook.select(1)

    # SECTION 5.10 - LAP TIMES CHART

    def _build_lap_times_chart(self, drivers):
        for w in self.tab_laps.winfo_children():
            w.destroy()

        laps = self.session.laps
        fig  = Figure(figsize=(9, 4.5), facecolor=BG_DARK)
        ax   = fig.add_subplot(111)
        ax.set_facecolor(BG_PANEL)

        legend_handles = []
        for drv in drivers:
            drv_laps = laps.pick_driver(drv).pick_quicklaps().sort_values("LapNumber")
            times    = drv_laps["LapTime"].dt.total_seconds()
            team     = drv_laps["Team"].iloc[0] if len(drv_laps) > 0 else ""
            colour   = get_team_colours(int(self.year_var.get())).get(team, ACCENT_GOLD)
            ax.plot(drv_laps["LapNumber"], times, color=colour, linewidth=2,
                    marker="o", markersize=3, alpha=0.9)
            legend_handles.append(mpatches.Patch(color=colour, label=drv))

        ax.set_title("Lap Times Per Lap", color=TEXT_PRIMARY, fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel("Lap Number", color=TEXT_DIM)
        ax.set_ylabel("Lap Time (s)", color=TEXT_DIM)
        ax.tick_params(colors=TEXT_DIM)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.legend(handles=legend_handles, facecolor=BG_CARD, labelcolor=TEXT_PRIMARY,
                  edgecolor=BORDER, fontsize=9)
        ax.grid(color=BORDER, linestyle="--", linewidth=0.5, alpha=0.5)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.tab_laps)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        canvas.draw()

    # SECTION 5.11 - TELEMETRY CHART

    def _build_telemetry_chart(self, drivers):
        for w in self.tab_telemetry.winfo_children():
            w.destroy()

        laps = self.session.laps
        fig  = Figure(figsize=(9, 5), facecolor=BG_DARK)
        axes = fig.subplots(3, 1, sharex=True)
        for ax in axes:
            ax.set_facecolor(BG_PANEL)

        axes[0].set_title("Fastest Lap Telemetry Comparison",
                          color=TEXT_PRIMARY, fontsize=12, fontweight="bold")

        for drv in drivers:
            drv_laps = laps.pick_driver(drv).pick_fastest()
            if drv_laps is None:
                continue
            tel    = drv_laps.get_telemetry()
            team   = laps[laps["Driver"] == drv]["Team"].iloc[0] \
                     if len(laps[laps["Driver"] == drv]) > 0 else ""
            colour = get_team_colours(int(self.year_var.get())).get(team, ACCENT_GOLD)
            axes[0].plot(tel["Distance"], tel["Speed"],    color=colour, linewidth=1.5, label=drv)
            axes[1].plot(tel["Distance"], tel["Throttle"], color=colour, linewidth=1.5)
            axes[2].plot(tel["Distance"], tel["Brake"],    color=colour, linewidth=1.5)

        for ax, lbl in zip(axes, ["Speed (km/h)", "Throttle (%)", "Brake"]):
            ax.set_ylabel(lbl, color=TEXT_DIM, fontsize=8)
            ax.tick_params(colors=TEXT_DIM)
            for spine in ax.spines.values():
                spine.set_color(BORDER)
            ax.grid(color=BORDER, linestyle="--", linewidth=0.4, alpha=0.5)

        axes[0].legend(facecolor=BG_CARD, labelcolor=TEXT_PRIMARY, edgecolor=BORDER, fontsize=9)
        axes[2].set_xlabel("Distance (m)", color=TEXT_DIM)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, self.tab_telemetry)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        canvas.draw()


# SECTION 6 - ENTRY POINT #

def main():
    app = F1Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()