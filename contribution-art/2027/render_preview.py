#!/usr/bin/env python3
"""Render the exact calendar layout with explicitly illustrative colors.

Pillow is needed only to recreate this documentation preview; the scheduler
and its tests use the Python standard library only.
"""
import calendar
import json
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1850, 615


def font(size, bold=False):
    paths = [
        Path('/usr/share/texmf/fonts/opentype/public/lm') /
        ('lmsans10-bold.otf' if bold else 'lmsans17-regular.otf'),
        Path('/usr/share/fonts/truetype/dejavu') /
        ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
    ]
    for path in paths:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    days, meta = plan['days'], plan['metadata']
    im = Image.new('RGB', (WIDTH, HEIGHT), '#ffffff')
    dr = ImageDraw.Draw(im)
    dark, muted = '#1f2328', '#656d76'
    dr.text((65, 43), 'WELCOME / 2027', fill=dark, font=font(49, True))
    dr.text((68, 108), 'momo-hub-learn  |  Normal development + darker lettering',
            fill=muted, font=font(27))
    dr.rounded_rectangle((62, 169, 1788, 480), radius=14,
                         fill='#ffffff', outline='#d0d7de', width=2)
    x0, y0, pitch, cell = 149, 236, 29, 22
    month_seen = set()
    for item in days:
        d = date.fromisoformat(item['date'])
        month = d.month
        if month not in month_seen:
            month_seen.add(month)
            dr.text((x0 + item['col'] * pitch, 190), calendar.month_abbr[month],
                    fill=dark, font=font(23))
        x, y = x0 + item['col'] * pitch, y0 + item['row'] * pitch
        # Background is a deterministic illustration, never historical data.
        if item['lit']:
            color = '#216e39'
        else:
            bucket = (item['col'] * 11 + item['row'] * 3) % 17
            color = '#eff2f5' if bucket < 3 else '#c7f0d0' if bucket < 11 else '#9be9a8'
        dr.rounded_rectangle((x, y, x + cell, y + cell), radius=4, fill=color)
    for row, label in [(1, 'Mon'), (3, 'Wed'), (5, 'Fri')]:
        dr.text((80, y0 + row * pitch - 2), label, fill=muted, font=font(21))
    dr.rounded_rectangle((1119, 446, 1136, 463), radius=3, fill='#c7f0d0')
    dr.text((1148, 441), 'Everyday work', fill=muted, font=font(21))
    dr.rounded_rectangle((1397, 446, 1414, 463), radius=3, fill='#216e39')
    dr.text((1426, 441), 'WELCOME dates', fill=muted, font=font(21))
    dr.text((68, 511),
            f"{meta['lit_days']} lettering days  /  +{meta['art_commits_per_lit_day']} art commits per day  /  "
            '07 Feb - 20 Nov 2027', fill=dark, font=font(26, True))
    dr.text((68, 558),
            'PLAN PREVIEW  |  Background and colors are illustrative. GitHub determines actual shades.',
            fill=muted, font=font(22))
    output = ROOT / 'preview.png'
    im.save(output, optimize=True)
    print(output)


if __name__ == '__main__':
    main()
