#!/usr/bin/env python3
"""Render site/index.html from the publication-safe snapshot.

Cards, gauge and archive are server-rendered so the page is fully readable
with JavaScript off. The markup mirrors the client-side renderer in template.html;
the category icons are read straight from the template so there is one source.
"""
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from math import floor, ceil
from zoneinfo import ZoneInfo
import base64
import html
import json
import re

from deal_logic import validated_offer, expired_record, parse_utc

ROOT = Path(__file__).resolve().parents[1]
ET = ZoneInfo('America/New_York')
VIS = ('screen', 'tools', 'toy', 'home', 'apparel')

snapshot = json.loads((ROOT / 'site/deals.json').read_text())
now = parse_utc(snapshot['generated_at'])
rows = [d for d in (validated_offer(x, now) for x in snapshot['deals']) if d]
assert all(Decimal(str(d['actual_percent_off'])) >= 35 for d in rows)
live_ids = {d['id'] for d in rows}
archive = [a for a in (snapshot.get('recently_expired') or []) if a.get('id') not in live_ids]
# Defensive: archive entries must have been valid at their own capture time.
archive = [a for a in archive if validated_offer({**a, 'source_type': 'retailer', 'evidence': a.get('evidence', 'archived')},
                                                 parse_utc(a['observed_at']) + timedelta(seconds=1))]

tpl = (ROOT / 'site/template.html').read_text()
ICONS = dict(re.findall(r"\b(screen|tools|toy|home|apparel):'(<svg.*?</svg>)'", tpl))
assert set(ICONS) == set(VIS), 'icon set missing from template'


def esc(v):
    return html.escape(str(v), quote=True)


def money(p):
    return f'${float(p):,.2f}'


def et(ts):
    t = parse_utc(ts).astimezone(ET)
    return t.strftime('%b ') + str(t.day) + ', ' + t.strftime('%I:%M %p').lstrip('0') + ' ET'


def pct_of(d):
    return floor((Decimal(str(d['reference_price'])) - Decimal(str(d['sale_price']))) / Decimal(str(d['reference_price'])) * 100)


def exact(d):
    return float((Decimal(str(d['reference_price'])) - Decimal(str(d['sale_price']))) / Decimal(str(d['reference_price'])) * 100)


def vis(d):
    return d.get('visual') if d.get('visual') in VIS else 'home'


def freshness(d):
    t, e = parse_utc(d['observed_at']), parse_utc(d['valid_until'])
    left = max(0.0, (e - now).total_seconds())
    f = max(0.0, min(1.0, left / max(1.0, (e - t).total_seconds())))
    label = f'Verified · expires in {int(left // 60)}m' if left < 3600 else f'Verified · expires in {int(left // 3600)}h'
    return f, left < 6 * 3600, label


def card(d):
    v, p = vis(d), pct_of(d)
    pay = max(2.0, min(100.0, float(d['sale_price']) / float(d['reference_price']) * 100))
    f, low, label = freshness(d)
    saved_amt = float(Decimal(str(d['reference_price'])) - Decimal(str(d['sale_price'])))
    return (
        f'<article class="deal" data-id="{esc(d["id"])}">'
        f'<div class="deal-head v-{v}"><div class="pct" aria-label="{p} percent off"><span class="pct-n">{p}</span><span class="pct-u"><b>%</b><span>OFF</span></span></div>{ICONS[v]}<span class="deal-cat">{esc(d["category"])}</span>'
        f'<button type="button" class="save" data-save="{esc(d["id"])}" aria-pressed="false" aria-label="Add to saved deals: {esc(d["title"])}"><svg class="ic bm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M6 3.5h12v17l-6-4.2-6 4.2z"/></svg></button></div>'
        f'<div class="deal-body"><span class="store">{esc(d["store"])}</span><h3>{esc(d["title"])}</h3>'
        f'<div class="prices"><span class="now">{money(d["sale_price"])}</span><span class="was"><span class="sr">Reference price </span>{money(d["reference_price"])}</span><span class="saveamt">SAVE {money(saved_amt)}</span></div>'
        f'<div class="bar" role="img" aria-label="You pay {round(pay)} percent of the reference price; the 35 percent line sits at 65 percent"><span class="bar-pay" style="width:{pay:.2f}%"></span><span class="bar-line" style="left:65%"></span></div>'
        f'<div class="bar-legend"><span>You pay {round(pay)}% of ref.</span><em>35% line</em></div>'
        f'<details class="math" data-math="{esc(d["id"])}"><summary>Show the math</summary><div class="receipt"><span class="eq">({money(d["reference_price"])} − {money(d["sale_price"])}) ÷ {money(d["reference_price"])} = {exact(d):.2f}%</span><br>Listed as {p}% (rounded down)<span class="ev">{esc(d["evidence"])}</span><br>Checked {et(d["observed_at"])} · <a href="{esc(d["source_url"])}" target="_blank" rel="noopener noreferrer">Evidence: {esc(d["source_name"])} ↗</a></div></details>'
        f'<div class="deal-foot"><div class="fresh{" low" if low else ""}"><span>{label}</span><i style="--f:{f:.3f}"></i></div><a class="go" href="{esc(d["url"])}" target="_blank" rel="noopener noreferrer">View deal <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9"/></svg></a></div>'
        f'</div></article>'
    )


def arch_row(d):
    return (f'<div class="arch-row"><div><b>{esc(d["title"])}</b><small>{esc(d["store"])} · last verified {et(d["observed_at"])}</small></div>'
            f'<div class="ap">{money(d["sale_price"])} <s>{money(d["reference_price"])}</s><br>was −{pct_of(d)}%</div>'
            f'<a href="{esc(d["url"])}" target="_blank" rel="noopener noreferrer">Check retailer ↗</a></div>')


def gauge(lst):
    max_p = max([60] + [ceil((pct_of(d) + 3) / 10) * 10 for d in lst])
    pos = lambda p: f'{p / max_p * 100:.2f}%'
    h = f'<div class="g-cut" style="width:{pos(35)}"><span>Cut zone<br>never listed</span></div><div class="g-track"></div><div class="g-line-label" style="left:{pos(35)}">35% LINE</div>'
    h += ''.join(f'<span class="g-tick" style="left:{pos(t)}">{t}%</span>' for t in range(0, max_p + 1, 10))
    placed = []
    for d in sorted(lst, key=pct_of):
        p = pct_of(d)
        i = sum(1 for q in placed if abs(q - p) < 2.5)
        placed.append(p)
        h += f'<span class="g-dot v-{vis(d)}" style="left:{pos(p)};bottom:{32 + i * 15}px" title="{esc(d["title"])} — {p}% off"></span>'
    return h


def ticker(lst):
    if not lst:
        return '<span class="ticker-item">Board clear · evidence refreshes every 30 minutes · nothing under 35% · ever</span>' * 4
    one = ''.join(f'<span class="ticker-item"><b>−{pct_of(d)}%</b>{esc(d["title"])} · {money(d["sale_price"])} @ {esc(d["store"])}</span>'
                  for d in sorted(lst, key=pct_of, reverse=True))
    return one + one


def chips(lst):
    cats = {}
    for d in lst:
        cats[d['category']] = cats.get(d['category'], 0) + 1
    out = f'<button type="button" class="chip" data-cat="all" aria-pressed="true">All <small>{len(lst)}</small></button>'
    out += ''.join(f'<button type="button" class="chip" data-cat="{esc(k)}" aria-pressed="false">{esc(k)} <small>{n}</small></button>' for k, n in sorted(cats.items()))
    return out


src = json.loads((ROOT / 'data/sources.json').read_text())
retailer_names = {d['store'] for d in snapshot['deals']} | {'Amazon', 'Best Buy', 'Walmart', 'Target', 'The Home Depot', 'Crutchfield'}


def src_card(s):
    proof = s['name'] in retailer_names or 'official retailer' in s.get('description', '').lower()
    tag = '<span class="tag proof">Proof · retailer</span>' if proof else '<span class="tag lead">Lead source</span>'
    return f'<a class="src" href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{tag}<strong>{esc(s["name"])}</strong><span>{esc(s["description"])} <i aria-hidden="true">↗</i></span></a>'



# ---------- Brand Watch ----------
brands_cfg = json.loads((ROOT / 'data/brands.json').read_text())
BRANDS = brands_cfg['brands']
ODDS = {'often': ('Often clears 35%', 3), 'sometimes': ('Sometimes clears 35%', 2), 'rarely': ('Rarely clears 35%', 1)}


def brand_matches(b, d):
    hay = d.get('store', '') if b.get('scope') == 'store' else f"{d.get('brand', '')} {d.get('title', '')}"
    return any(re.search(r'(?<![A-Za-z0-9])' + re.escape(m) + r'(?![A-Za-z0-9])', hay, re.I) for m in b['match'])


def brand_card(b):
    label, lvl = ODDS.get(b['odds'], ODDS['sometimes'])
    n = sum(1 for d in rows if brand_matches(b, d))
    live = f'{n} live on the board' if n else 'Nothing qualifying right now'
    parent = ('<span class="brand-parent">' + esc(b['parent']) + '</span>') if b.get('parent') and b.get('parent') != b.get('category') else ''
    meter = ''.join(f'<i class="{"on" if k < lvl else ""}"></i>' for k in range(3))
    return (f'<article class="bw-card" data-brand="{esc(b["id"])}">'
            f'<div class="brand-top"><div><span class="brand-cat">{esc(b["category"])}</span><h3>{esc(b["name"])}</h3>{parent}</div>'
            f'<button type="button" class="follow" data-follow="{esc(b["id"])}" aria-pressed="false" aria-label="Follow {esc(b["name"])}"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Follow</button></div>'
            f'<div class="odds odds-{esc(b["odds"])}"><span class="meter" aria-hidden="true">{meter}</span>{label}</div>'
            f'<dl><dt>Where it shows up</dt><dd>{esc(b["where"])}</dd><dt>Watch out</dt><dd>{esc(b["trap"])}</dd></dl>'
            f'<div class="brand-foot"><span class="live-n{" has" if n else ""}" data-live="{esc(b["id"])}">{live}</span>'
            f'<button type="button" class="seebtn{"" if n else " hidden"}" data-see="{esc(b["id"])}">See deals →</button></div></article>')


# ---------- Sale calendar ----------
from datetime import date
cal = json.loads((ROOT / 'data/calendar.json').read_text())
R0, R1 = (date.fromisoformat(x) for x in cal['range'])
DAYS = (R1 - R0).days + 1
TBA_END = date(2026, 11, 30)
KIND = {'early': 'Early sale', 'main': 'Main event', 'cyber': 'Cyber Monday', 'day': 'One-day'}


def fmt_day(dt):
    return dt.strftime('%b ') + str(dt.day)


def cal_html():
    pos = lambda d: f'{((d - R0).days) / DAYS * 100:.3f}%'
    width = lambda a, b: f'{((b - a).days + 1) / DAYS * 100:.3f}%'
    head = '<div class="cal-axis"><div class="cal-name"></div><div class="cal-days">'
    for i in range(DAYS):
        d = R0 + timedelta(days=i)
        mk = next((m['label'] for m in cal['markers'] if m['date'] == d.isoformat()), '')
        cls = 'wk' if d.weekday() >= 5 else ''
        cls += ' mk' if mk else ''
        lab = (d.strftime('%b').upper() + ' ' if d.day == 1 else '') + str(d.day)
        abbr = {'Thanksgiving': 'TG', 'Black Friday': 'BF', 'Cyber Monday': 'CM'}.get(mk, '')
        if abbr:
            lab += f'<small>{abbr}</small>'
        head += f'<span class="{cls.strip()}" title="{esc(mk)}">{lab}</span>'
    head += '</div></div>'
    bands = ''.join(f'<span class="cal-band" style="left:{pos(date.fromisoformat(m["date"]))};width:{width(date.fromisoformat(m["date"]), date.fromisoformat(m["date"]))}"><b>{esc(m["label"])}</b></span>' for m in cal['markers'])
    body = ''
    listing = ''
    for r in cal['retailers']:
        evs = r['events']
        bars = ''
        if not evs:
            bars = f'<span class="cal-na">{esc(r.get("note", "Not announced"))}</span>'
            listing += f'<li><b>{esc(r["name"])}</b> — {esc(r.get("note", "Not announced"))}</li>'
        for k, e in enumerate(evs):
            a = date.fromisoformat(e['start'])
            tba = e['end'] is None
            if tba:
                nxt = [date.fromisoformat(x['start']) for x in evs[k + 1:]]
                b = (min(nxt) - timedelta(days=1)) if nxt else TBA_END
            else:
                b = date.fromisoformat(e['end'])
            clip = a < R0
            a2 = max(a, R0)
            when = (fmt_day(a) + (' → end TBA' if tba else ('' if a == b else ' – ' + fmt_day(b)))) if not tba else fmt_day(a) + ' → end TBA'
            title = f'{r["name"]}: {e["name"]} · {when}'
            bars += (f'<span class="ev ev-{e["kind"]}{" tba" if tba else ""}{" clip" if clip else ""}" style="left:{pos(a2)};width:{width(a2, b)}" '
                     f'data-start="{a.isoformat()}" data-end="{b.isoformat()}" data-tba="{int(tba)}" data-name="{esc(e["name"])}" data-retailer="{esc(r["name"])}" title="{esc(title)}"><span>{esc(e["name"])}</span></span>')
            listing += f'<li><b>{esc(r["name"])}</b> — {esc(e["name"])}: {when}' + (f' ({esc(e["detail"])})' if e.get('detail') else '') + '</li>'
        body += f'<div class="cal-row"><div class="cal-name">{esc(r["name"])}</div><div class="cal-track">{bars}</div></div>'
    overlay = f'<div class="cal-overlay" aria-hidden="true">{bands}<span class="cal-today" id="calToday" style="left:{pos(now.astimezone(ET).date())}"><b>Today</b></span></div>'
    return (f'<div class="cal" role="img" aria-label="Timeline of announced 2026 Black Friday sale events by retailer; full list follows.">{head}<div class="cal-body">{overlay}{body}</div></div>',
            f'<ul class="cal-list">{listing}</ul>')


CAL_CHART, CAL_LIST = cal_html()

ps = [pct_of(d) for d in rows]
safe_json = json.dumps({**snapshot, 'deals': rows, 'recently_expired': archive}, ensure_ascii=False) \
    .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
sorted_rows = sorted(rows, key=lambda d: (-pct_of(d), -(d['reference_price'] - d['sale_price'])))

values = {
    'DEAL_COUNT': str(len(rows)),
    'MAX_DISCOUNT': str(max(ps, default=0)),
    'AVG_DISCOUNT': str(round(sum(ps) / len(ps)) if ps else 0),
    'STORE_COUNT': str(len({d['store'] for d in rows})),
    'DEAL_CARDS': ''.join(card(d) for d in sorted_rows),
    'GAUGE': gauge(rows),
    'TICKER': ticker(rows),
    'CATEGORY_CHIPS': chips(rows),
    'STORE_OPTIONS': ''.join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in sorted({d['store'] for d in rows})),
    'CHECKED_LABEL': et(snapshot['generated_at']),
    'EXPIRED_ROWS': ''.join(arch_row(a) for a in archive),
    'EXPIRED_COUNT': str(len(archive)),
    'ARCHIVE_HIDDEN': '' if archive else ' hidden',
    'SOURCE_CARDS': ''.join(src_card(s) for s in src['research_sources']),
    'PAYLOAD_JSON': safe_json,
    'LOGO_URI': 'data:image/png;base64,' + base64.b64encode((ROOT / 'site/assets/cdg-logo.png').read_bytes()).decode(),
    'MARK_NAVY_URI': 'data:image/png;base64,' + base64.b64encode((ROOT / 'site/assets/cdg-mark-navy.png').read_bytes()).decode(),
    'BRAND_CARDS': ''.join(brand_card(b) for b in BRANDS),
    'BRANDS_JSON': json.dumps([{k: b[k] for k in ('id', 'name', 'match', 'scope') if k in b} for b in BRANDS], ensure_ascii=False).replace('<', '\\u003c'),
    'CAL_CHART': CAL_CHART,
    'CAL_LIST': CAL_LIST,
    'CAL_SOURCE': f'<a href="{esc(cal["source"]["url"])}" target="_blank" rel="noopener noreferrer">{esc(cal["source"]["name"])} ↗</a>',
}
for key, value in values.items():
    tpl = tpl.replace('{{' + key + '}}', value)
assert '{{' not in tpl, 'unfilled placeholder'
(ROOT / 'site/index.html').write_text(tpl)
print(f'Built site/index.html — {len(rows)} live cards, {len(archive)} recently expired.')
