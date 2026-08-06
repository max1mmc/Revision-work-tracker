# Revision / work tracker

A revision log that lives in your terminal. Type `rev`, see your heatmap, log
what you just did, get on with it.

Your log is **yours** — it's kept in `~/.revision` on your own machine, not in
this repo. Cloning this gets you the program and an empty tracker.

## Type `rev`

That's the whole interface. You get the heatmap drawn in the terminal, and a
prompt underneath:

```
  REVISION TRACKER  ·  Thu 06 Aug 2026

    13h10 this week   ▲ 15m vs last   6d streak (best 8d)   341h55 all time

      Feb Mar  Apr May  Jun Jul  Aug
      ▀▄█▀▀▄█▀▀▀▄█▀▄▀▀█▄▀▀▄█▀▀▄▀█▀▄▀
    0 ▁▂▃▄▅▆▇█ 4h+

    30 days  ▃▁▇▂·▅▄▆·▂▇
    Physics    ████████████ 87h05
    English    █████████░░░ 71h25
    …

  log it → 90 chem past paper
```

Type how long and what you did, hit enter, and it redraws with the square
filled in. Blank line quits. `undo` and `open` work at the prompt too.

Durations: `90`, `45m`, `1h30`, `2h`. Subjects autocomplete against ones you've
already used, so `chem` becomes `Chemistry` rather than starting a second
subject with a different spelling.

## Or skip the prompt

```sh
rev 90 Chemistry                  # straight in, no dashboard
rev 1h30 Maths "C4 past paper"
rev -d yesterday 60 Biology       # backdated (also -d 01/08, -d -3)

rev open          # the full dashboard, in a browser
rev list          # last 10 entries (rev list 30 for more)
rev undo          # remove the most recent entry
rev stats         # totals and streak
rev where         # where your log is kept
```

Log as many sessions a day as you like — they add up into that day's total.

## The browser dashboard

`rev open` builds `~/.revision/dashboard.html` and opens it. One self-contained
file — no server, no internet, no dependencies.

- **Heatmap** — a square per day, coloured on **Turbo**, the actual scientific
  heatmap colormap: blue for a light day, through cyan, green and yellow, into
  orange, red and deep red for your heaviest. Hover for that day's breakdown.
  The scale tops out at your 90th-percentile day, so ordinary days spread across
  the middle of the ramp instead of all sitting at the cold end.
- **Trend** — daily minutes for 90 days with a 7-day rolling average over the
  top, which is where a slide or a build-up actually shows.
- **Subject mix, week by week** — 26 weeks of stacked bars. The one that catches
  a subject you've quietly stopped touching.
- **Which days you actually work** — average minutes per weekday.
- **Tiles** — this week against last, total, streak, average active day, best day.

## Where the data lives

`~/.revision/data.csv`, one row per session:

```csv
date,minutes,subject,notes
2026-08-06,90,Chemistry,kinetics
```

Plain text — edit it by hand or in a spreadsheet, then `rev build`.

Set `REV_HOME` to keep it somewhere else — a synced folder, or a **private**
repo if you want it backed up and version controlled:

```sh
export REV_HOME=~/my-private-revision-log
rev save          # commits and pushes, if REV_HOME is a git repo
```

## Setup

Needs Python 3 (already there on macOS and most Linux).

```sh
git clone https://github.com/max1mmc/Revision-work-tracker.git
echo 'alias rev="~/Revision-work-tracker/rev"' >> ~/.zshrc && source ~/.zshrc
rev
```

Bash users: `~/.bashrc` instead of `~/.zshrc`.
