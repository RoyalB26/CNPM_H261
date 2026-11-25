"""Kiểm tra gợi ý Hub không phân bổ tài nguyên đã bị giữ."""

import copy
import asyncio
from unittest.mock import patch
import httpx
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.memory_store import MockDatabaseStore
from user.hubs import available_bikes, hub_detail, search_hubs, suggest_route
from user.schemas.hub import SearchHubQuery, RouteSuggestionRequest


class HubTests(unittest.TestCase):
    def setUp(self):
        async def road(url, **kwargs):
            from user.hubs import distance
            points = [tuple(map(float, pair.split(','))) for pair in url.rsplit('/', 1)[-1].split(';')]
            km = sum(distance(a[1], a[0], b[1], b[0]) for a, b in zip(points, points[1:]))
            return httpx.Response(200, request=httpx.Request('GET', url), json={
                'code': 'Ok', 'routes': [{'distance': km * 1000, 'duration': km * 240,
                'geometry': {'type': 'LineString', 'coordinates': points}}]})
        source = patch('httpx.AsyncClient.get', side_effect=road)
        source.start()
        self.addCleanup(source.stop)
        self.db = MockDatabaseStore()
        self.query = RouteSuggestionRequest(origin_lat=10.8753, origin_lng=106.8005,
                                            dest_lat=10.8805, dest_lng=106.8055)

    def test_search_without_accents_and_read_only(self):
        before = copy.deepcopy(self.db.__dict__)
        hubs = search_hubs(self.db, SearchHubQuery(keyword='BACH KHOA'))
        self.assertEqual([h['id'] for h in hubs], ['hub-02'])
        self.assertEqual(before, self.db.__dict__)

    def test_library_bike_count_matches_bookable_list_without_changing_shared_counter(self):
        """Hub seed báo 6 nhưng chỉ có XE-101: response User phải báo đúng 1."""
        hub = self.db.get_hub('hub-05')
        before = copy.deepcopy(self.db.__dict__)
        view = hub_detail(self.db, hub)
        self.assertEqual(view.available_bikes, 1)
        self.assertEqual([bike.id for bike in view.bikes], ['XE-101'])
        self.assertEqual(hub['available_bikes'], 6)
        self.assertEqual(before, self.db.__dict__)

    def test_bike_views_exclude_holds_active_rides_maintenance_and_relocations(self):
        """Các Hub dùng cùng điều kiện khả dụng khi xem số lượng và chọn xe."""
        hub = self.db.get_hub('hub-02')
        self.assertNotIn('error', self.db.create_booking({
            'plan_type': 'rental', 'hub_id': hub['id'], 'resource_name': 'XE-052'}))
        self.db.maintenance_tickets.append({'device_code': 'XE-061', 'hub_id': hub['id'], 'status': 'PENDING'})
        before = copy.deepcopy(self.db.__dict__)
        for stored in self.db.hubs:
            view = hub_detail(self.db, stored)
            self.assertEqual(view.available_bikes, len(view.bikes))
            self.assertEqual([bike.id for bike in view.bikes], [bike['id'] for bike in available_bikes(self.db, stored)])
        self.assertEqual(hub_detail(self.db, hub).available_bikes, 0)
        self.assertEqual(hub_detail(self.db, self.db.get_hub('hub-03')).available_bikes, 0)
        self.assertEqual(before, self.db.__dict__)

    def test_bike_count_tracks_reserve_cancel_start_and_cross_hub_return(self):
        """Giữ/hủy/di chuyển xe không làm số hiển thị lệch danh sách chọn đặt."""
        self.db.user['active_services']['ride'] = None
        origin = self.db.get_hub('hub-05')
        target = self.db.get_hub('hub-04')
        target_before = hub_detail(self.db, target).available_bikes
        payload = {'plan_type': 'rental', 'hub_id': origin['id'], 'resource_name': 'XE-101',
                   'destination_hub_id': target['id']}
        booking = self.db.create_booking(payload)
        self.assertNotIn('error', booking)
        self.assertEqual(hub_detail(self.db, origin).available_bikes, 0)
        self.assertNotIn('error', self.db.cancel_booking(booking['id']))
        self.assertEqual(hub_detail(self.db, origin).available_bikes, 1)
        booking = self.db.create_booking(payload)
        self.assertNotIn('error', booking)
        ride = self.db.start_ride(booking['id'])
        self.assertTrue(ride['success'])
        self.assertEqual(hub_detail(self.db, origin).available_bikes, 0)
        returned = self.db.return_vehicle(ride['ride']['trip_id'], target['name'])
        self.assertTrue(returned['success'])
        self.assertEqual(hub_detail(self.db, origin).available_bikes, 0)
        view = hub_detail(self.db, target)
        self.assertEqual(view.available_bikes, target_before + 1)
        self.assertIn('XE-101', [bike.id for bike in view.bikes])

    def test_inactive_or_zero_counter_hub_has_no_bookable_bikes_in_response(self):
        for change in ({'status': 'DEACTIVATED'}, {'available_bikes': 0}):
            with self.subTest(change=change):
                hub = copy.deepcopy(self.db.get_hub('hub-05'))
                hub.update(change)
                view = hub_detail(self.db, hub)
                self.assertEqual(view.available_bikes, 0)
                self.assertEqual(view.bikes, [])

    def test_suggestion_skips_seed_active_ride_and_held_bikes(self):
        result = asyncio.run(suggest_route(self.db, self.query))
        self.assertNotEqual(result.recommended_bike.id, 'XE-024')
        self.assertEqual(result.destination_hub.id, 'hub-02')

    def test_inactive_and_full_hubs_not_recommended(self):
        self.db.get_hub('hub-01')['status'] = 'DEACTIVATED'
        self.db.get_hub('hub-02')['available_parking'] = 0
        result = asyncio.run(suggest_route(self.db, self.query))
        self.assertNotEqual(result.origin_hub.id, 'hub-01')
        self.assertNotEqual(result.destination_hub.id, 'hub-02')
        for hub in self.db.hubs:
            hub['available_parking'] = 0
        with self.assertRaises(ValueError):
            asyncio.run(suggest_route(self.db, self.query))

    def test_relocation_held_bikes_excluded(self):
        self.assertEqual(available_bikes(self.db, self.db.get_hub('hub-03')), [])

    def test_empty_network(self):
        self.db.hubs = []
        with self.assertRaises(ValueError):
            asyncio.run(suggest_route(self.db, self.query))

    def test_hub_view_subtracts_incoming_hold_without_mutating_store(self):
        hub = self.db.get_hub('hub-02')
        hub['available_parking'] = 3
        self.db.relocations.append({'target_hub_id': hub['id'], 'status': 'PENDING',
                                    'total_bikes': 2, 'reserved_slot_ids': ['P11', 'P12']})
        before = copy.deepcopy(self.db.__dict__)
        self.assertEqual(hub_detail(self.db, hub).available_parking, 1)
        self.assertEqual(before, self.db.__dict__)
        self.db.relocations[-1]['status'] = 'COMPLETED'
        self.assertEqual(hub_detail(self.db, hub).available_parking, 3)

    def test_reserved_destination_excluded_from_search_and_route(self):
        hub = self.db.get_hub('hub-02')
        hub['available_parking'] = 1
        self.db.relocations.append({'target_hub_id': hub['id'], 'status': 'PENDING',
                                    'total_bikes': 1, 'reserved_slot_ids': ['P11']})
        result = asyncio.run(suggest_route(self.db, self.query))
        self.assertNotEqual(result.destination_hub.id, hub['id'])
        found = search_hubs(self.db, SearchHubQuery(vehicle_type='personal'))
        self.assertNotIn(hub['id'], [h['id'] for h in found])
