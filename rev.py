#!/usr/bin/env python3
"""Revision / work tracker.

Log a session in one line, then the dashboard rebuilds itself.

    rev 90 Chemistry                 # 90 minutes of Chemistry, today
    rev 1h30 Maths "C4 past paper"   # with a note
    rev -d 2026-08-01 45 Physics     # backdated
    rev list                         # recent entries
    rev undo                         # remove the last entry
    rev build                        # just regenerate index.html
    rev push                         # commit + push to GitHub
"""

import csv
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.csv")
TEMPLATE = os.path.join(ROOT, "tracker", "template.html")
OUTPUT = os.path.join(ROOT, "index.html")
FIELDS = ["date", "minutes", "subject", "notes"]


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
        "stats": {
            "totalMinutes": sum(totals.values()),
            "sessions": len(rows),
            "currentStreak": current,
            "longestStreak": longest,
            "last7": sum(m for d, m in totals.items() if d >= week_ago),
            "activeDays": len(totals),
        },
        "generated": datetime.now().strftime("%d %b %Y, %H:%M"),
    }


def build():
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


def cmd_add(args):
    when = date.today()
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-d", "--date"):
            when = parse_date(args[i + 1])
            i += 2
            continue
        rest.append(a)
        i += 1
    if len(rest) < 2:
        sys.exit("usage: rev <duration> <subject> [note] [-d <date>]")
    minutes = parse_duration(rest[0])
    subject = rest[1]
    note = " ".join(rest[2:])

    rows = read_rows()
    rows.append({
        "date": when.isoformat(),
        "minutes": str(minutes),
        "subject": subject,
        "notes": note,
    })
    write_rows(rows)
    build()
    today_total = daily_totals(rows)[when.isoformat()]
    print(f"logged {fmt(minutes)} of {subject}"
          + (f" ({note})" if note else "")
          + f" on {when:%a %d %b} — {fmt(today_total)} that day")


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
    print(f"rebuilt index.html from {build()} entries")


def cmd_push(args):
    build()
    msg = " ".join(args) or f"Update tracker — {date.today():%d %b %Y}"
    subprocess.run(["git", "add", "data.csv", "index.html"], cwd=ROOT, check=True)
    r = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT)
    if r.returncode == 0:
        subprocess.run(["git", "push"], cwd=ROOT, check=True)


COMMANDS = {
    "list": cmd_list, "ls": cmd_list,
    "undo": cmd_undo,
    "stats": cmd_stats,
    "build": cmd_build,
    "push": cmd_push, "sync": cmd_push,
}


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        return print(__doc__.strip())
    handler = COMMANDS.get(argv[0])
    try:
        (handler(argv[1:]) if handler else cmd_add(argv))
    except ValueError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main(sys.argv[1:])
