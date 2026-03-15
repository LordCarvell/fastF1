# F1 Dashboard

A desktop app for exploring Formula 1 session data. Built with Python, Tkinter, FastF1, and Matplotlib. You can browse race results, compare lap times between drivers, and look at telemetry data for any session from 2018 to the current season.

> **Author:** <!-- your name / GitHub username here -->

---

## Features

- **Season and round browser** - select any season from 2018 onwards. For the current year, only completed rounds are shown
- **Smart session selector** - detects sprint weekends automatically and only shows the sessions that actually happened (no FP3 on a sprint weekend for example)
- **Overview tab** - shows key stats like fastest lap, driver count, and a colour-coded lap time box plot for the top 10 drivers
- **Lap Times tab** - plots lap time progression for any drivers you select
- **Telemetry tab** - compares speed, throttle, and brake traces from each driver's fastest lap
- **Results tab** - full results table with best lap times, gap to leader, and DNF/DNS status
- **Team colours** - uses the correct colours per season, including the 2026 grid where Audi replaces Kick Sauber and Cadillac joins
- **Caching** - downloaded session data is saved locally so repeat loads are instant

---

## Requirements

- Python 3.9 or newer
- pip packages:

```
fastf1
matplotlib
```

---

## Installation

**1. Clone or download the repo**

```bash
git clone https://github.com/yourusername/f1-dashboard.git
cd f1-dashboard
```

Or just download `main.py` on its own.

**2. Install the dependencies**

```bash
pip install fastf1 matplotlib
```

**3. Run it**

```bash
python main.py
```

On first run it will create an `f1_cache/` folder in the same directory. FastF1 saves session data there so you only have to download each session once.

---

## How to Use

1. Pick a **season** from the dropdown
2. Pick a **round** - if you are on the current season it only shows completed races and defaults to the most recent one
3. Pick a **session** - the list updates based on whether it is a sprint or standard weekend
4. Click **LOAD SESSION** - first load downloads the data, after that it loads from cache
5. Select one or more **drivers** from the sidebar (hold Ctrl to select multiple)
6. Click **PLOT SELECTED** to see the Lap Times and Telemetry tabs fill in

---

## Project Structure

```
f1-dashboard/
├── main.py        # whole application in one file
├── f1_cache/      # created automatically, holds cached session data
└── README.md
```

---

## Known Issues

- **First load is slow** - FastF1 downloads data from the F1 API on first load. A full race can take 30 to 60 seconds depending on your connection. After that it is instant from cache
- **2026 team colours are placeholder** - Audi and Cadillac colours are best guesses for now. You can update them in the `_TEAM_COLOURS_2026` dict near the top of `main.py`
- **DNF detection is not perfect** - a driver gets marked as DNF if they completed 3 or more laps fewer than the race distance. Most retirements are caught but edge cases like post-race exclusions will not be flagged correctly
- **Needs internet for uncached sessions** - there is no offline fallback if a session has not been downloaded yet
- **Practice results are a bit meaningless** - the results tab sorts by best lap time which makes sense for qualifying but does not really reflect anything useful in a practice session

---

## Roadmap

- [ ] Tyre strategy view (compound and stint data per driver)
- [ ] Sector time comparison
- [ ] Circuit map with position overlay
- [ ] Export charts as PNG
- [ ] Driver standings table
- [ ] Constructor standings table
- [ ] Qualifying head-to-head delta chart
- [ ] Pit stop timing analysis

---

## Built With

- [FastF1](https://github.com/theOehrly/Fast-F1) - F1 timing and telemetry data
- [Matplotlib](https://matplotlib.org/) - charts and plots
- [Tkinter](https://docs.python.org/3/library/tkinter.html) - GUI (comes with Python)
