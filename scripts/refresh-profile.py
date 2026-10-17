"""Render Lam's profile cards from GitHub's public contribution calendar."""
from datetime import date, timedelta
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = "artnguyen23"


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.labels = {}
        self.tooltip = None
        self.header = False
        self.heading = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            self.cells[attrs["id"]] = (date.fromisoformat(attrs["data-date"]), int(attrs["data-level"]))
        if tag == "tool-tip":
            self.tooltip = attrs.get("for")
            if self.tooltip:
                self.labels[self.tooltip] = ""
        if tag == "h2" and attrs.get("id") == "js-contribution-activity-description":
            self.header = True

    def handle_data(self, data):
        if self.tooltip:
            self.labels[self.tooltip] += data
        if self.header:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tooltip = None
        if tag == "h2":
            self.header = False

    def calendar(self):
        if not 350 <= len(self.cells) <= 378:
            raise ValueError("GitHub calendar is missing or incomplete; keep the previous cards.")
        days = []
        for key, (day, level) in self.cells.items():
            match = re.match(r"(No|[\d,]+) contributions? on ", self.labels.get(key, ""))
            if match is None or not 0 <= level <= 4:
                raise ValueError(f"Unrecognized calendar day: {day}")
            count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            days.append((day, level, count))
        days.sort()
        if any(b[0] - a[0] != timedelta(days=1) for a, b in zip(days, days[1:])):
            raise ValueError("Calendar dates are not consecutive.")
        total = sum(day[2] for day in days)
        heading = re.search(r"([\d,]+)\s+contributions", " ".join(self.heading))
        if heading is None or int(heading[1].replace(",", "")) != total:
            raise ValueError("Contribution total does not match the calendar.")
        return days, total


def text(x, y, value, color, size=16, **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def svg(height, title, content):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title">
<title id="title">{escape(title)}</title>
<g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif">{content}</g>
</svg>\n'''


def picture(stem, alt, version):
    return f'''<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/{stem}-dark.svg?v={version}">
  <source media="(prefers-color-scheme: light)" srcset="./assets/{stem}-light.svg?v={version}">
  <img src="./assets/{stem}-light.svg?v={version}" width="100%" alt="{escape(alt, quote=True)}">
</picture>'''


def render(days, total):
    cards = {}
    for mode in ("light", "dark"):
        dark = mode == "dark"
        bg, ink, muted, accent = ("#192f27", "#e1f1e8", "#a1bbaf", "#9bcdb0") if dark else ("#f1f7f2", "#355648", "#778d7d", "#83ac8c")
        colors = ["#263f33", "#385e45", "#548666", "#7db18d", "#bbe4ba"] if dark else ["#e2ece2", "#c4ddc3", "#a0c9a5", "#78ab85", "#518464"]
        repo = f'<rect width="1000" height="124" rx="20" fill="{bg}"/>'
        repo += text(34, 32, "REPOSITORY", muted, 11, letter_spacing=2)
        repo += text(34, 72, "SArOS", ink, 29, font_weight=500)
        repo += text(34, 102, "artnguyen23 / SArOS", muted, 15)
        repo += f'<rect x="861" y="46" width="74" height="28" rx="14" fill="{colors[0]}"/>'
        repo += text(898, 65, "Public", muted, 12, text_anchor="middle")
        repo += text(962, 71, "↗", accent, 24, text_anchor="middle")
        cards[f"repository-{mode}.svg"] = svg(124, "Repository: SArOS, public. Open repository.", repo)

        body = f'<rect width="1000" height="300" rx="20" fill="{bg}"/>'
        body += text(34, 46, "Contributions", ink, 25, font_weight=500)
        body += text(966, 44, f"{total:,} in the last year", muted, 16, text_anchor="end")
        start = days[0][0] - timedelta(days=(days[0][0].weekday() + 1) % 7)
        grid_x, grid_y, step, cell = 68, 100, 16, 12
        last_month = None
        last_label = -100
        for day, level, count in days:
            offset = (day - start).days
            col, row = offset // 7, offset % 7
            x, y = grid_x + col * step, grid_y + row * step
            if day.month != last_month:
                if (day != days[0][0] or day.day <= 7) and col - last_label >= 3:
                    body += text(x, 82, day.strftime("%b"), muted, 12)
                    last_label = col
                last_month = day.month
            label = f"{day.isoformat()}: {count} contribution{'s' if count != 1 else ''}"
            body += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{colors[level]}"><title>{label}</title></rect>'
        for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
            body += text(34, grid_y + row * step + 10, label, muted, 10)
        body += text(34, 261, f"Public GitHub calendar · Updated {days[-1][0].strftime('%d %b %Y')}", muted, 12)
        body += text(788, 261, "Less", muted, 11, text_anchor="end")
        for level, color in enumerate(colors):
            body += f'<rect x="{800 + level * 17}" y="249" width="12" height="12" rx="3" fill="{color}"/>'
        body += text(893, 261, "More", muted, 11)
        cards[f"contributions-{mode}.svg"] = svg(300, f"{total:,} contributions in the last year. Updated {days[-1][0].isoformat()}.", body)

    version = sha256("".join(cards.values()).encode()).hexdigest()[:12]
    banner = '''<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/lam-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/lam-light.svg">
  <img src="./assets/lam-light.svg" width="100%" alt="Hi, I'm Lam. It's nice to have you here. A quiet mint landscape with a little firefly.">
</picture>'''
    readme = banner + '\n\n<a href="https://github.com/artnguyen23/SArOS">\n' + picture("repository", "SArOS · Public repository", version) + '\n</a>\n\n' + picture("contributions", f"{total:,} contributions in the last year; updated {days[-1][0].isoformat()}", version) + '\n'
    for name, content in cards.items():
        (ROOT / "assets" / name).write_text(content)
    (ROOT / "README.md").write_text(readme)
    print(f"Rendered {len(days)} calendar days, {total} contributions, and SArOS.")


def main():
    request = Request(f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "Lam-profile-card/1.0", "Accept-Language": "en-US"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode()
    parser = CalendarParser()
    parser.feed(html)
    render(*parser.calendar())


if __name__ == "__main__":
    main()
