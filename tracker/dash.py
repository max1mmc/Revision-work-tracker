"""Terminal dashboard: the heatmap, in colour, in your shell."""

import os
import shutil
from datetime import date, datetime, timedelta

# Blue -> cyan -> green -> yellow -> orange -> red -> dark red.
STOPS = [
    (0.00, (40, 90, 180)),
    (0.14, (0, 150, 205)),
    (0.28, (0, 190, 175)),
    (0.42, (110, 205, 110)),
    (0.56, (225, 225, 80)),
    (0.68, (248, 190, 55)),
    (0.79, (242, 140, 40)),
    (0.89, (228, 70, 40)),
    (0.96, (186, 25, 30)),
    (1.00, (116, 10, 22)),
]
EMPTY = (44, 49, 60)
SPARKS = "▁▂▃▄▅▆▇█"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"


def colour(t):
    t = max(0.0, min(1.0, t))
    for i in range(1, len(STOPS)):
        p1, c1 = STOPS[i]
        if t <= p1:
            p0, c0 = STOPS[i - 1]
            k = (t - p0) / (p1 - p0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return STOPS[-1][1]


def fg(rgb):
    return "\x1b[38;2;%d;%d;%dm" % rgb


def bg(rgb):
    return "\x1b[48;2;%d;%d;%dm" % rgb


def fmt(minutes):
    h, m = divmod(int(minutes), 60)
    if not h:
        return f"{m}m"
    return f"{h}h{m:02d}" if m else f"{h}h"


def heatmap(totals, cap, weeks):
    """GitHub-style grid, two days per character cell via half-blocks."""
    today = date.today()
    start = today - timedelta(weeks=weeks - 1)
    start -= timedelta(days=start.weekday())          # back to Monday

    cells = []                                        # cells[week][weekday]
    labels = []
    d = start
    while d <= today + timedelta(days=6 - today.weekday()):
        col = []
        for _ in range(7):
            col.append(None if d > today else totals.get(d.isoformat(), 0))
            if d.day <= 7:
                labels.append((len(cells), MONTHS[d.month - 1]))
            d += timedelta(days=1)
        cells.append(col)

    def paint(v):
        if v is None:
            return None
        return colour(min(1.0, v / cap)) if v else EMPTY

    # month strip
    strip = [" "] * len(cells)
    used = -9
    for week, name in labels:
        if week - used >= 4 and week + 3 <= len(cells):
            strip[week:week + 3] = list(name)
            used = week
    out = ["    " + DIM + "".join(strip) + RESET]

    for pair in range(0, 7, 2):
        row = "    "
        for col in cells:
            top, bot = paint(col[pair]), paint(col[pair + 1]) if pair + 1 < 7 else None
            if top is None and bot is None:
                row += RESET + " "
            elif bot is None:
                row += RESET + fg(top) + "▀"
            elif top is None:
                row += RESET + fg(bot) + "▄"
            else:
                row += fg(top) + bg(bot) + "▀"
        out.append(row + RESET)
    return out


def legend(cap, width=24):
    ramp = "".join(fg(colour(i / (width - 1))) + "█" for i in range(width))
    return f"    {DIM}0{RESET} {ramp}{RESET} {DIM}{fmt(cap)}+{RESET}"


def sparkline(totals, cap, days=30):
    today = date.today()
    out = ""
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        v = totals.get(d, 0)
        if not v:
            out += DIM + "·" + RESET
            continue
        t = min(1.0, v / cap)
        out += fg(colour(t)) + SPARKS[min(len(SPARKS) - 1, int(t * len(SPARKS)))]
    return out + RESET


def bars(subjects, cap, width=22):
    if not subjects:
        return []
    top = subjects[0]["minutes"]
    n = max(1, len(subjects) - 1)
    rows = []
    for i, s in enumerate(subjects[:8]):
        filled = max(1, round(width * s["minutes"] / top))
        c = colour(1 - (i / n) * 0.85)
        rows.append(f"    {s['name'][:14]:<14} {fg(c)}{'█' * filled}{RESET}"
                    f"{DIM}{'░' * (width - filled)}{RESET} {fmt(s['minutes']):>6}")
    return rows


def render(payload, totals):
    """Full dashboard as a list of lines."""
    cols = shutil.get_terminal_size((90, 30)).columns
    # only draw back as far as there's history, so a new log isn't a grey slab
    span = 12
    if payload["days"]:
        first = datetime.strptime(payload["days"][0]["date"], "%Y-%m-%d").date()
        span = (date.today() - first).days // 7 + 2
    weeks = max(12, min(53, cols - 8, span))
    s, cap = payload["stats"], payload["cap"]
    today = date.today()

    this_week = sum(m for d, m in totals.items()
                    if d >= (today - timedelta(days=today.weekday())).isoformat())
    prev_start = today - timedelta(days=today.weekday() + 7)
    last_week = sum(m for d, m in totals.items()
                    if prev_start.isoformat() <= d < (prev_start + timedelta(days=7)).isoformat())
    delta = this_week - last_week
    arrow = (fg((110, 205, 110)) + "▲ " + fmt(abs(delta)) if delta > 0
             else fg((228, 70, 40)) + "▼ " + fmt(abs(delta)) if delta < 0
             else DIM + "level")

    L = []
    L.append("")
    L.append(f"  {BOLD}REVISION TRACKER{RESET}{DIM}"
             f"{today.strftime('  ·  %a %d %b %Y')}{RESET}")
    L.append("")
    L.append(f"  {BOLD}{fmt(this_week):>7}{RESET} this week   "
             f"{arrow}{RESET}{DIM} vs last{RESET}   "
             f"{BOLD}{s['currentStreak']}d{RESET}{DIM} streak (best "
             f"{s['longestStreak']}d){RESET}   "
             f"{BOLD}{fmt(s['totalMinutes'])}{RESET}{DIM} all time{RESET}")
    L.append("")
    L += heatmap(totals, cap, weeks)
    L.append("")
    L.append(legend(cap))
    if s["activeDays"]:
        L.append("")
        L.append(f"    {DIM}30 days{RESET} {sparkline(totals, cap)}")
        L.append("")
        L += bars(payload["subjects"], cap)
    L.append("")
    return L


def show(payload, totals, clear=True):
    if clear and os.isatty(1):
        print("\x1b[2J\x1b[H", end="")
    print("\n".join(render(payload, totals)))
