#!/usr/bin/env python3
"""Revision / work tracker.

    rev                              # the dashboard, and a prompt to log
    rev 90 Chemistry                 # or log straight from the command line
    rev 1h30 Maths "C4 past paper"   # with a note
    rev -d 2026-08-01 45 Physics     # backdated
    rev list                         # recent entries
    rev undo                         # remove the last entry
    rev open                         # open the full dashboard in a browser
    rev where                        # where your log is kept

Your log lives in ~/.revision, not in this repo — set REV_HOME to move it.
"""

import csv
import json
import os
import re
import shlex
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "tracker", "template.html")
FIELDS = ["date", "minutes", "subject", "notes"]

# Your log lives outside the repo. The repo is the program; the data is yours,
# it stays on your machine, and cloning this gets you an empty tracker of your
# own. Point REV_HOME somewhere else (a private repo, a synced folder) to move it.
HOME = os.path.abspath(os.environ.get("REV_HOME")
                       or os.path.expanduser("~/.revision"))
DATA = os.path.join(HOME, "data.csv")
OUTPUT = os.path.join(HOME, "dashboard.html")


def ensure_home():
    os.makedirs(HOME, exist_ok=True)
    stale = os.path.join(ROOT, "data.csv")      # from before the data moved out
    if os.path.exists(stale) and not os.path.exists(DATA):
        os.replace(stale, DATA)
        print(f"moved your log out of the repo into {DATA}")


# ---------------------------------------------------------------- parsing

def parse_duration(text):
    """'90' -> 90, '1h30' -> 90, '2h' -> 120, '45m' -> 45, '1.5h' -> 90."""
    s = text.strip().lower().replace(" ", "")
    m = re.fullmatch(r"(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m?)?", s)
    if not m or not any(m.groups()):
        raise ValueError(f"can't read a duration from {text!r}")
    hours = float(m.group(1) or 0)
    mins = float(m.group(2) or 0)
    total = round(hours * 60 + mins)
    if total <= 0:
        raise ValueError("duration must be more than zero")
    return total


def parse_date(text):
    t = text.strip().lower()
    today = date.today()
    if t in ("today", "t"):
        return today
    if t in ("yesterday", "y"):
        return today - timedelta(days=1)
    if re.fullmatch(r"-\d+", t):                       # -1, -2 = days ago
        return today + timedelta(days=int(t))
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m", "%d-%m"):
        try:
            d = datetime.strptime(t, fmt).date()
            return d.replace(year=today.year) if "%Y" not in fmt else d
        except ValueError:
            continue
    raise ValueError(f"can't read a date from {text!r}")


# ---------------------------------------------------------------- storage

def read_rows():
    if not os.path.exists(DATA):
        return []
    with open(DATA, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("date")]


def write_rows(rows):
    ensure_home()
    rows.sort(key=lambda r: (r["date"], r["subject"].lower()))
    with open(DATA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- stats

def daily_totals(rows):
    totals = defaultdict(int)
    for r in rows:
        totals[r["date"]] += int(r["minutes"])
    return totals


def streaks(days):
    """Current and longest run of consecutive days with any revision."""
    if not days:
        return 0, 0
    ds = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in days)
    longest = run = 1
    for prev, cur in zip(ds, ds[1:]):
        run = run + 1 if (cur - prev).days == 1 else 1
        longest = max(longest, run)
    today = date.today()
    current = 0
    cursor = today if ds[-1] == today else today - timedelta(days=1)
    seen = set(ds)
    while cursor in seen:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def scale_cap(totals):
    """Top of the colour scale: the 90th-percentile day, so ordinary days
    still spread across the whole blue->red range instead of all sitting blue."""
    vals = sorted(totals.values())
    if len(vals) < 14:
        return 180          # too little history to read a percentile from
    p90 = vals[int(len(vals) * 0.9) - 1]
    return max(90, int(round(p90 / 30.0) * 30))


def build_payload(rows):
    totals = daily_totals(rows)
    by_subject = defaultdict(int)
    notes = defaultdict(list)
    for r in rows:
        by_subject[r["subject"]] += int(r["minutes"])
        label = r["subject"]
        if r.get("notes"):
            label += f" — {r['notes']}"
        notes[r["date"]].append({"label": label, "minutes": int(r["minutes"])})
    current, longest = streaks(totals.keys())
    week_ago = (date.today() - timedelta(days=6)).isoformat()

    # week-by-week subject mix, so a neglected subject is visible
    weeks = defaultdict(lambda: defaultdict(int))
    for r in rows:
        d = datetime.strptime(r["date"], "%Y-%m-%d").date()
        monday = (d - timedelta(days=d.weekday())).isoformat()
        weeks[monday][r["subject"]] += int(r["minutes"])
    week_list = [{"start": k, "bySubject": dict(v), "total": sum(v.values())}
                 for k, v in sorted(weeks.items())][-26:]

    # average minutes per weekday, counting only weeks you were active
    per_weekday = defaultdict(list)
    if totals:
        d = datetime.strptime(min(totals), "%Y-%m-%d").date()
        while d <= date.today():
            per_weekday[d.weekday()].append(totals.get(d.isoformat(), 0))
            d += timedelta(days=1)
    weekday = [round(sum(v) / len(v)) if v else 0
               for _, v in sorted(per_weekday.items())] or [0] * 7

    this_monday = date.today() - timedelta(days=date.today().weekday())
    this_week = sum(m for d, m in totals.items() if d >= this_monday.isoformat())
    prev = this_monday - timedelta(days=7)
    last_week = sum(m for d, m in totals.items()
                    if prev.isoformat() <= d < this_monday.isoformat())
    best_day = max(totals.items(), key=lambda kv: kv[1]) if totals else ("", 0)
    best_week = max(week_list, key=lambda w: w["total"]) if week_list else None

    return {
        "days": [
            {"date": d, "minutes": m, "sessions": notes[d]}
            for d, m in sorted(totals.items())
        ],
        "subjects": sorted(
            ({"name": k, "minutes": v} for k, v in by_subject.items()),
            key=lambda s: -s["minutes"],
        ),
        "cap": scale_cap(totals),
        "weeks": week_list,
        "weekday": weekday,
        "stats": {
            "totalMinutes": sum(totals.values()),
            "sessions": len(rows),
            "currentStreak": current,
            "longestStreak": longest,
            "last7": sum(m for d, m in totals.items() if d >= week_ago),
            "activeDays": len(totals),
            "thisWeek": this_week,
            "lastWeek": last_week,
            "bestDay": {"date": best_day[0], "minutes": best_day[1]},
            "bestWeek": best_week["total"] if best_week else 0,
        },
        "generated": datetime.now().strftime("%d %b %Y, %H:%M"),
    }


def build():
    ensure_home()
    rows = read_rows()
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    payload = json.dumps(build_payload(rows), separators=(",", ":"))
    html = html.replace("/*__DATA__*/null", payload)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    return len(rows)


# ---------------------------------------------------------------- commands

def fmt(minutes):
    h, m = divmod(int(minutes), 60)
    if not h:
        return f"{m}m"
    return f"{h}h {m}m" if m else f"{h}h"


def match_subject(name, rows):
    """Keep spellings consistent: 'chem' becomes the existing 'Chemistry'."""
    known = {r["subject"] for r in rows}
    for k in known:
        if k.lower() == name.lower():
            return k
    hits = [k for k in known if k.lower().startswith(name.lower())]
    return hits[0] if len(hits) == 1 else name[:1].upper() + name[1:]


def add_entry(args):
    """Shared by the command line and the prompt. Returns a summary line."""
    when = date.today()
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-d", "--date", "on"):
            when = parse_date(args[i + 1])
            i += 2
            continue
        rest.append(a)
        i += 1
    if len(rest) < 2:
        raise ValueError("say how long and what — e.g. 90 chemistry past paper")
    minutes = parse_duration(rest[0])
    rows = read_rows()
    subject = match_subject(rest[1], rows)
    note = " ".join(rest[2:])

    rows.append({
        "date": when.isoformat(),
        "minutes": str(minutes),
        "subject": subject,
        "notes": note,
    })
    write_rows(rows)
    build()
    day_total = daily_totals(rows)[when.isoformat()]
    return (f"logged {fmt(minutes)} of {subject}"
            + (f" — {note}" if note else "")
            + f" on {when:%a %d %b}; {fmt(day_total)} that day")


def cmd_add(args):
    print(add_entry(args))


def cmd_list(args):
    n = int(args[0]) if args else 10
    rows = read_rows()[-n:]
    if not rows:
        return print("nothing logged yet")
    for r in rows:
        d = datetime.strptime(r["date"], "%Y-%m-%d").date()
        line = f"{d:%a %d %b}  {fmt(r['minutes']):>7}  {r['subject']}"
        if r["notes"]:
            line += f"  ({r['notes']})"
        print(line)


def cmd_undo(_):
    rows = read_rows()
    if not rows:
        return print("nothing to undo")
    gone = rows.pop()
    write_rows(rows)
    build()
    print(f"removed {fmt(gone['minutes'])} of {gone['subject']} on {gone['date']}")


def cmd_stats(_):
    s = build_payload(read_rows())["stats"]
    print(f"total       {fmt(s['totalMinutes'])} over {s['activeDays']} days")
    print(f"last 7 days {fmt(s['last7'])}")
    print(f"streak      {s['currentStreak']} days (best {s['longestStreak']})")


def cmd_build(_):
    n = build()
    print(f"rebuilt {OUTPUT} from {n} entries")


def cmd_where(_):
    print(f"log        {DATA}")
    print(f"dashboard  {OUTPUT}")
    print(f"program    {ROOT}")
    print(f"\nSet REV_HOME to keep the log somewhere else "
          f"(a private repo, iCloud, Dropbox).")


def cmd_open(_):
    build()
    subprocess.run(["open", OUTPUT])


def cmd_save(args):
    """Commit the log wherever it lives — only useful if REV_HOME is a repo."""
    build()
    if not os.path.isdir(os.path.join(HOME, ".git")):
        sys.exit(f"{HOME} isn't a git repo — nothing to save to.\n"
                 f"Point REV_HOME at a private repo if you want your log backed up.")
    msg = " ".join(args) or f"Revision log — {date.today():%d %b %Y}"
    subprocess.run(["git", "add", "-A"], cwd=HOME, check=True)
    if subprocess.run(["git", "commit", "-m", msg], cwd=HOME).returncode == 0:
        subprocess.run(["git", "push"], cwd=HOME)


def cmd_dash(_=None):
    """No arguments: show the dashboard, then sit on a prompt."""
    sys.path.insert(0, os.path.join(ROOT, "tracker"))
    import dash

    while True:
        rows = read_rows()
        dash.show(build_payload(rows), daily_totals(rows))
        if not os.isatty(0):
            return
        try:
            line = input("  \x1b[2mlog it →\x1b[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line or line in ("q", "quit", "exit"):
            build()
            return
        try:
            if line in ("undo", "u"):
                cmd_undo(None)
            elif line in ("open", "o"):
                cmd_open(None)
            else:
                print("  \x1b[32m✓\x1b[0m " + add_entry(shlex.split(line)))
        except ValueError as e:
            print(f"  \x1b[31m✗\x1b[0m {e}")
        input("  \x1b[2m[enter]\x1b[0m")


COMMANDS = {
    "list": cmd_list, "ls": cmd_list,
    "undo": cmd_undo,
    "stats": cmd_stats,
    "build": cmd_build,
    "open": cmd_open,
    "where": cmd_where,
    "save": cmd_save,
}


def main(argv):
    if not argv:
        return cmd_dash()
    if argv[0] in ("-h", "--help", "help"):
        return print(__doc__.strip())
    handler = COMMANDS.get(argv[0])
    try:
        (handler(argv[1:]) if handler else cmd_add(argv))
    except ValueError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
