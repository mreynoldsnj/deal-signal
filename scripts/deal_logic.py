"""Fail-closed deal validation; zero discounts below 35% are publishable."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from math import floor
import re

MIN_DISCOUNT = Decimal('35')
ALLOWED_SCHEMES = {'https'}


def parse_utc(s):
    dt = datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must include an offset')
    return dt.astimezone(timezone.utc)


def validated_offer(item, now=None):
    """Return normalized item only with enough evidence for the 35% threshold."""
    now = now or datetime.now(timezone.utc)
    required = ('id', 'title', 'store', 'category', 'sale_price', 'reference_price', 'url', 'source_url', 'source_name', 'observed_at', 'valid_until', 'evidence')
    if any(not item.get(k) for k in required):
        return None
    if item.get('source_type') != 'retailer':
        return None
    try:
        sale = Decimal(str(item['sale_price']))
        reference = Decimal(str(item['reference_price']))
        observed = parse_utc(item['observed_at'])
        valid_until = parse_utc(item['valid_until'])
        pct = (reference - sale) / reference * Decimal('100')
    except (InvalidOperation, ValueError, TypeError, ZeroDivisionError):
        return None
    if sale <= 0 or reference <= sale or pct < MIN_DISCOUNT:
        return None
    if observed > now or valid_until <= now or (now - observed).total_seconds() > 86400:
        return None
    # Never grant more than 24 hours of freshness from evidence capture.
    if (valid_until - observed).total_seconds() > 86400:
        return None
    for key in ('url', 'source_url'):
        parsed = urlparse(str(item[key]))
        if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname or parsed.username or parsed.password:
            return None
    evidence_host = urlparse(item['source_url']).hostname or ''
    retailer_host = urlparse(item['url']).hostname or ''
    # Both must be the same official merchant parent domain; disallow aggregator redirect as proof.
    root = lambda h: '.'.join(h.lower().split('.')[-2:])
    if root(evidence_host) != root(retailer_host):
        return None
    item = dict(item)
    item['sale_price'] = float(sale)
    item['reference_price'] = float(reference)
    item['percent_off'] = floor(pct)  # conservative; never round 34.9% up to 35%
    item['actual_percent_off'] = round(float(pct), 2)
    item['amount_saved'] = round(float(reference - sale), 2)
    return item


def verify_documented_prices(text, product_keyword, sale, reference):
    """Conservative proximity check: matching model/title and both prices within same window.

    This is corroboration ONLY; dynamic sites/HTML may not expose product prices.
    Never silently mark a stale deal as checked on a non-match.
    """
    compact = re.sub(r'\s+', ' ', text).lower()
    product_keyword = re.sub(r'\s+', ' ', product_keyword).lower()
    sale_form = f'${Decimal(str(sale)):,.2f}'
    ref_form = f'${Decimal(str(reference)):,.2f}'
    sale_re = re.escape(sale_form.lower())
    ref_re = re.escape(ref_form.lower())
    positions = [m.start() for m in re.finditer(re.escape(product_keyword), compact)]
    for pos in positions:
        chunk = compact[max(0, pos - 140): min(len(compact), pos + 420)]
        if re.search(sale_re, chunk) and re.search(ref_re, chunk):
            return True
    return False


ARCHIVE_WINDOW_SECONDS = 7 * 86400


def expired_record(item, now=None):
    """Return a display-safe archive record for an offer that WAS valid but no longer is.

    The offer must pass every validated_offer() rule as of its own capture time
    (so the price pair, threshold, URLs and freshness window were sound), must not
    be valid now, and must have been captured within the last seven days. Archive
    records are never shown as live deals; they exist so an empty board can still
    explain what was recently on it.
    """
    now = now or datetime.now(timezone.utc)
    try:
        observed = parse_utc(item['observed_at'])
    except (KeyError, ValueError, TypeError):
        return None
    if validated_offer(item, now):
        return None
    if observed > now or (now - observed).total_seconds() > ARCHIVE_WINDOW_SECONDS:
        return None
    from datetime import timedelta
    at_capture = validated_offer(item, observed + timedelta(seconds=1))
    if not at_capture:
        return None
    keep = ('id', 'title', 'brand', 'store', 'category', 'sale_price', 'reference_price', 'url',
            'source_url', 'source_name', 'observed_at', 'valid_until', 'visual',
            'percent_off', 'actual_percent_off', 'amount_saved')
    rec = {k: at_capture[k] for k in keep if k in at_capture}
    rec['status'] = 'expired_unverified'
    return rec
