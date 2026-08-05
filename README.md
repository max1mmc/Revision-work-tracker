# Revision / work tracker

Log a revision session in one line. The dashboard rebuilds itself every time.

![heatmap](https://img.shields.io/badge/dashboard-index.html-blue)

## Log a session

```sh
rev 90 Chemistry                  # 90 minutes of Chemistry, today
rev 1h30 Maths "C4 past paper"    # hours + minutes, with a note
rev 45m Physics waves             # 45 minutes
rev -d yesterday 60 Biology       # backdated
rev -d 2026-08-01 2h English      # any date (also 01/08, -3 for "3 days ago")
```

Log as many sessions a day as you like — they add up into that day's total.

## Everything else

```sh
rev list          # last 10 entries (rev list 30 for more)
rev undo          # remove the most recent entry
rev stats         # totals and streak in the terminal
rev build         # regenerate index.html
rev push          # commit data.csv + index.html and push to GitHub
```

## The dashboard

Open `index.html` in a browser. It's a single self-contained file — no server, no
internet, no dependencies.

- **Heatmap** — one square per day for the whole history, coloured on a proper
  heat scale: deep blue for a light day, through cyan, green and yellow, into
  orange, red and dark red for your heaviest. Hover a square for the day's
  breakdown. The scale tops out at your 90th-percentile day, so ordinary days
  spread across the middle of the ramp instead of all sitting at the cold end.
- **Trend** — daily minutes for the last 90 days with a 7-day rolling average
  line over the top, which is where a slide or a build-up actually shows.
- **Subjects** — total time per subject, biggest first.
- **Tiles** — total logged, last 7 days, current and best streak, days revised,
  average active day.

## Where the data lives

`data.csv`, one row per session:

```csv
date,minutes,subject,notes
2026-08-05,90,Chemistry,past paper
```

Plain text, so you can edit it by hand or in a spreadsheet — run `rev build`
afterwards. Since it's in git, every push is a backup.

## Setup

Needs Python 3 (already on macOS). Add the shortcut to your shell:

```sh
echo 'alias rev="~/Revision-work-tracker/rev"' >> ~/.zshrc && source ~/.zshrc
```

To see the dashboard as a web page, turn on GitHub Pages under
**Settings → Pages → Deploy from branch → main / root**. It'll be at
`https://max1mmc.github.io/Revision-work-tracker/` after each `rev push`.
