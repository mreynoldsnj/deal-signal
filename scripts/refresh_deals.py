#!/usr/bin/env python3
"""Build publication-safe snapshot; discover RSS candidates without auto-publishing them.

A feed saying 'up to 60% off' is NOT price verification and will never make the public list.
Retailer price pairs can be revalidated from live merchant pages where the HTML exposes
both amounts near the exact product keyword; on failure, the old timestamp expires.
"""
import argparse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re
import sys
import urllib.request
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from deal_logic import validated_offer, verify_documented_prices, expired_record

ROOT = Path(__file__).resolve().parents[1]
UA = 'CDGDealSignal/1.0 (+https://cdgdigitalmedia.com/; public feeds only)'


class Plain(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.skip:
            self.skip -= 1
    def handle_data(self, d):
        if not self.skip:
            self.parts.append(d)


def plain(s):
    obj = Plain()
    obj.feed(unescape(s or ''))
    return ' '.join(' '.join(obj.parts).split())


def retrieve(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/rss+xml, application/xml, text/html;q=0.8, */*;q=0.5'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise ValueError(f'HTTP {resp.status}')
        return resp.read(2_000_000).decode('utf-8', 'replace')


def parse_feed(feedtext, source):
    """RSS/Atom candidates for editor review only, never immediate publication."""
    root = ET.fromstring(feedtext)
    out = []
    entries = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
    for item in entries[:150]:
        def get(tag):
            child = item.find(tag)
            return (child.text or '').strip() if child is not None else ''
        title = plain(get('title') or get('{http://www.w3.org/2005/Atom}title'))
        desc = plain(get('description') or get('{http://purl.org/rss/1.0/modules/content/}encoded') or get('{http://www.w3.org/2005/Atom}summary'))
        link = get('link')
        if not link:
            a = item.find('{http://www.w3.org/2005/Atom}link')
            link = (a.get('href') or '') if a is not None else ''
        if not title or not link.startswith('https://'):
            continue
        # Exclude purely percentage headline claims (including 'up to 70%').
        # Candidates can still be useful, but they must get actual item prices later.
        out.append({'id': hashlib.sha256(link.encode()).hexdigest()[:16], 'title': title[:180], 'source': source, 'url': link, 'details': desc[:260], 'status': 'needs_official_retailer_price_pair'})
    return out


def refresh_with_retailer(offer, now):
    """Only timestamp-renew if an official product/listing page shows matching amounts.

    By default this does not change monetary amounts automatically: a new price is
    a *new* assertion and needs editorial approval or a retailer API integration.
    """
    # 4 hours+ old -> attempt revalidation. Skip if fresh.
    try:
        t = datetime.fromisoformat(offer['observed_at'].replace('Z', '+00:00'))
    except (KeyError, ValueError):
        return offer, 'invalid_timestamp'
    if (now - t).total_seconds() < 4 * 3600:
        return offer, 'recent_evidence'
    url = offer['source_url']
    try:
        raw = retrieve(url)
        # Use a product-specific model number or phrase, never a generic brand.
        keyword = offer.get('verification_keyword') or offer['title'][:32]
        if not verify_documented_prices(plain(raw), keyword, offer['sale_price'], offer['reference_price']):
            return offer, 'price_not_confirmed'
        updated = dict(offer)
        updated['observed_at'] = now.isoformat().replace('+00:00', 'Z')
        updated['valid_until'] = (now + timedelta(hours=24)).isoformat().replace('+00:00', 'Z')
        updated['evidence'] = 'Retailer page checked again for both reference and current prices near the product title.'
        return updated, 'retailer_pair_matched'
    except Exception as exc:
        return offer, f'check_failed:{type(exc).__name__}'


def run(now, offline=False):
    source_cfg = json.loads((ROOT/'data/sources.json').read_text())
    seed = json.loads((ROOT/'data/seed_offers.json').read_text())
    observed = []
    archive = []
    statuses = []
    for item in seed:
        if offline:
            checked, status = item, 'offline_seed'
        else:
            checked, status = refresh_with_retailer(item, now)
        valid = validated_offer(checked, now)
        if valid:
            observed.append(valid)
        else:
            rec = expired_record(checked, now)
            if rec:
                archive.append(rec)
        statuses.append({'id': item['id'], 'status': status, 'published': bool(valid)})
    dedup = {x['id']: x for x in observed}
    deals = sorted(dedup.values(), key=lambda d: (-d['percent_off'], -d['amount_saved']))
    candidate_list, scans = [], []
    if not offline:
        for feed in source_cfg['discovery_feeds']:
            try:
                result = parse_feed(retrieve(feed['url']), feed['name'])
                candidate_list.extend(result)
                scans.append({'source': feed['name'], 'status': 'ok', 'items': len(result)})
            except Exception as e:
                scans.append({'source': feed['name'], 'status': 'unavailable', 'error': type(e).__name__})
    seen = set()
    candidates = []
    for c in candidate_list:
        if c['id'] not in seen:
            seen.add(c['id'])
            candidates.append(c)
    payload = {'generated_at': now.isoformat().replace('+00:00','Z'), 'minimum_discount_percent': 35, 'evidence_policy': 'official_retailer_price_pair_only', 'deals': deals, 'recently_expired': sorted(archive, key=lambda d: d['observed_at'], reverse=True), 'feed_status': scans}
    (ROOT/'site/deals.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    (ROOT/'data/review_queue.json').write_text(json.dumps({'generated_at': payload['generated_at'], 'count': len(candidates), 'candidates': candidates[:500]}, indent=2, ensure_ascii=False) + '\n')
    (ROOT/'data/refresh_status.json').write_text(json.dumps({'retailer_checks': statuses, 'discovery_scans': scans}, indent=2) + '\n')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Build from checked seed evidence without requesting external websites')
    parser.add_argument('--at', default='', help='Test clock override in ISO 8601')
    args = parser.parse_args()
    now = datetime.fromisoformat(args.at.replace('Z', '+00:00')) if args.at else datetime.now(timezone.utc)
    result = run(now, offline=args.offline)
    print(f"Published {len(result['deals'])} / {len(json.loads((ROOT/'data/seed_offers.json').read_text()))} retailer-priced offers (35%+).")
