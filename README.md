# Revision / work tracker

Log a revision session in one line. The dashboard rebuilds itself every time.

![heatmap](https://img.shields.io/badge/dashboard-index.html-blue)

## Type `rev`

That's the whole thing. You get the dashboard in the terminal — heatmap, streak,
last 30 days, subject bars — and a prompt underneath:

```
  REVISION TRACKER  ·  Wed 05 Aug 2026

    3h15 this week   ▲ 40m vs last   4d streak (best 15d)   408h all time

  log it → 90 chemistry past paper
```

Type how long and what you did, hit enter, and the dashboard redraws with it in.
Blank line quits. `undo` and `push` work at the prompt too.

Durations: `90`, `45m`, `1h30`, `2h`. Subjects autocomplete from ones you've
already used, so `chem` becomes `Chemistry` rather than a second subject.

## Or skip the prompt

```sh
rev 90 Chemistry                  # straight in, no dashboard
rev 1h30 Maths "C4 past paper"
rev -d yesterday 60 Biology       # backdated (also -d 01/08, -d -3)
rev list          # last 10 entries (rev list 30 for more)
rev undo          # remove the most recent entry
rev build         # regenerate index.html
rev push          # commit data.csv + index.html and push to GitHub
```

Log as many sessions a day as you like — they add up into that day's total.

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
- **Subject mix, week by week** — 26 weeks of stacked bars. This is the one that
  catches a subject you've quietly stopped touching.
- **Which days you actually work** — average minutes per weekday.
- **Subjects** — total time per subject, biggest first.
- **Tiles** — this week against last week, total, streak, average active day,
  best day ever.

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
