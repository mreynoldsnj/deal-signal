import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]/'scripts'))
from deal_logic import validated_offer, verify_documented_prices, expired_record

NOW = datetime(2026,11,10,9,15,tzinfo=timezone.utc)
BASE = {'id':'p', 'title':'Product', 'store':'Example Shop', 'category':'Tech','sale_price':'65','reference_price':'100', 'url':'https://store.example.com/a','source_url':'https://store.example.com/a','source_name':'Example Shop','observed_at':'2026-11-10T09:00:00Z','valid_until':'2026-11-11T09:00:00Z','evidence':'Item and both prices shown.','source_type':'retailer'}

class VerifyRules(unittest.TestCase):
    def test_exact_boundary(self):
        self.assertEqual(validated_offer(BASE, NOW)['percent_off'],35)
    def test_just_under_35_excluded(self):
        self.assertIsNone(validated_offer({**BASE,'sale_price':'65.01'},NOW))
    def test_34_point_9_excluded(self):
        self.assertIsNone(validated_offer({**BASE,'sale_price':'65.10'},NOW))
    def test_missing_old_price_excluded(self):
        self.assertIsNone(validated_offer({**BASE,'reference_price':None},NOW))
    def test_source_report_not_published(self):
        self.assertIsNone(validated_offer({**BASE,'source_type':'deal_blog'},NOW))
    def test_stale_excluded(self):
        self.assertIsNone(validated_offer(BASE,NOW+timedelta(days=2)))
    def test_future_excluded(self):
        self.assertIsNone(validated_offer(BASE,NOW-timedelta(days=1)))
    def test_http_excluded(self):
        self.assertIsNone(validated_offer({**BASE,'url':'http://store.example.com/a'},NOW))
    def test_mismatched_merchant_excluded(self):
        self.assertIsNone(validated_offer({**BASE,'source_url':'https://deals-other.com/x'},NOW))
    def test_oversized_freshness_excluded(self):
        self.assertIsNone(validated_offer({**BASE,'valid_until':'2026-11-12T09:00:00Z'},NOW))
    def test_retailer_evidence_proximity(self):
        self.assertTrue(verify_documented_prices('LG C6 TV Amount was $1,799.99 Save $800.00 $999.99', 'LG C6 TV',999.99,1799.99))
    def test_different_prices_dont_pass(self):
        self.assertFalse(verify_documented_prices('LG C6 TV Amount was $1,799.99 Save $800.00 $1,299.99', 'LG C6 TV',999.99,1799.99))
    def test_live_offer_not_archived(self):
        self.assertIsNone(expired_record(BASE, NOW))
    def test_expired_offer_archived_unverified(self):
        rec = expired_record(BASE, NOW+timedelta(days=2))
        self.assertIsNotNone(rec)
        self.assertEqual(rec['status'], 'expired_unverified')
        self.assertEqual(rec['percent_off'], 35)
    def test_archive_window_is_seven_days(self):
        self.assertIsNone(expired_record(BASE, NOW+timedelta(days=8)))
    def test_sub_threshold_never_archived(self):
        self.assertIsNone(expired_record({**BASE,'sale_price':'65.10'}, NOW+timedelta(days=2)))

if __name__ == '__main__': unittest.main()
