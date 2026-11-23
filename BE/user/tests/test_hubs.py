"""Kiểm tra gợi ý Hub không phân bổ tài nguyên đã bị giữ."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.hubs import available_bikes, search_hubs, suggest_route
from user.schemas.hub import SearchHubQuery, RouteSuggestionRequest


class HubTests(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabaseStore()
        self.query = RouteSuggestionRequest(origin_lat=10.8753, origin_lng=106.8005,
                                            dest_lat=10.8805, dest_lng=106.8055)

    def test_search_without_accents_and_read_only(self):
        before = copy.deepcopy(self.db.__dict__)
        hubs = search_hubs(self.db, SearchHubQuery(keyword='BACH KHOA'))
        self.assertEqual([h['id'] for h in hubs], ['hub-02'])
        self.assertEqual(before, self.db.__dict__)

    def test_suggestion_skips_seed_active_ride_and_held_bikes(self):
        result = suggest_route(self.db, self.query)
        self.assertNotEqual(result.recommended_bike.id, 'XE-024')
        self.assertEqual(result.destination_hub.id, 'hub-02')

    def test_inactive_and_full_hubs_not_recommended(self):
        self.db.get_hub('hub-01')['status'] = 'DEACTIVATED'
        self.db.get_hub('hub-02')['available_parking'] = 0
        result = suggest_route(self.db, self.query)
        self.assertNotEqual(result.origin_hub.id, 'hub-01')
        self.assertNotEqual(result.destination_hub.id, 'hub-02')
        for hub in self.db.hubs:
            hub['available_parking'] = 0
        with self.assertRaises(ValueError):
            suggest_route(self.db, self.query)

    def test_relocation_held_bikes_excluded(self):
        self.assertEqual(available_bikes(self.db, self.db.get_hub('hub-03')), [])

    def test_empty_network(self):
        self.db.hubs = []
        with self.assertRaises(ValueError):
            suggest_route(self.db, self.query)
