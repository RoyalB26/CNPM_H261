"""Kiểm tra quét nền, khóa dùng chung và tính nguyên vẹn khi lưu JSON lỗi."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.json_store import JsonStateStore, PersistenceError
from shared.memory_store import MockDatabaseStore
from user.expiry_worker import expiry_interval, run_expiry_worker, sweep_expired_bookings


class ExpiryWorkerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="user-expiry-")
        self.addCleanup(self.directory.cleanup)
        self.db = MockDatabaseStore()
        self.db.user['active_services'].update(ride=None, charging=None, parking=None)
        self.storage = JsonStateStore(self.db, Path(self.directory.name) / 'runtime.json')
        self.lock = asyncio.Lock()

    def hold(self, **payload):
        result = self.db.create_booking(payload)
        self.assertNotIn('error', result)
        return result

    async def test_sweep_all_resource_types_persists_and_releases_once(self):
        before = {h['id']: {key: h[key] for key in ('available_bikes', 'available_parking',
                  'available_chargers', 'available_batteries')} for h in self.db.hubs}
        bookings = [
            self.hold(plan_type='rental', hub_id='hub-02', resource_name='XE-052'),
            self.hold(plan_type='parking', hub_id='hub-02', personal_plate='59-A1 888.88', parking_slot='P11'),
            self.hold(plan_type='charging', hub_id='hub-01', personal_plate='59-A1 888.88', charging_port='S01'),
            self.hold(plan_type='swap', hub_id='hub-02', battery_type='B48', battery_quantity=2),
            self.hold(plan_type='personal', hub_id='hub-04', personal_plate='59-A1 777.77'),
        ]
        now = datetime.now(timezone.utc)
        for booking in bookings:
            booking['expires_at'] = (now - timedelta(seconds=1)).isoformat()
        ids = await sweep_expired_bookings(self.storage, self.lock, now)
        self.assertCountEqual(ids, [b['id'] for b in bookings])
        for booking_id in ids:
            stored = next(b for b in self.db.bookings if b['id'] == booking_id)
            self.assertEqual(stored['status'], 'Hết hạn')
            self.assertNotIn('rental_invoice', stored)
        for hub in self.db.hubs:
            for key, expected in before[hub['id']].items():
                self.assertEqual(hub[key], expected, (hub['id'], key))
        saved = self.storage.path.read_bytes()
        snapshot = self.storage.snapshot()
        self.assertEqual(await sweep_expired_bookings(self.storage, self.lock, now), [])
        self.assertEqual(snapshot, self.storage.snapshot())
        self.assertEqual(saved, self.storage.path.read_bytes())
        reloaded = JsonStateStore(MockDatabaseStore(), self.storage.path)
        reloaded.reload()
        self.assertEqual(snapshot, reloaded.snapshot())

    async def test_no_expired_booking_does_not_write(self):
        self.hold(plan_type='swap', hub_id='hub-02', battery_type='B48')
        with patch.object(self.storage, '_write') as write:
            self.assertEqual(await sweep_expired_bookings(self.storage, self.lock), [])
            write.assert_not_called()

    async def test_write_failure_keeps_ram_and_disk_then_retry_succeeds(self):
        booking = self.hold(plan_type='rental', hub_id='hub-02', resource_name='XE-052')
        booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        self.storage.commit(lambda candidate: None)
        before = self.storage.snapshot()
        disk = self.storage.path.read_bytes()
        with patch.object(self.storage, '_write', side_effect=PersistenceError('Lỗi ghi mô phỏng')):
            with self.assertRaises(PersistenceError):
                await sweep_expired_bookings(self.storage, self.lock)
        self.assertEqual(before, self.storage.snapshot())
        self.assertEqual(disk, self.storage.path.read_bytes())
        self.assertEqual(await sweep_expired_bookings(self.storage, self.lock), [booking['id']])

    async def test_worker_waits_for_request_lock(self):
        booking = self.hold(plan_type='swap', hub_id='hub-02', battery_type='B48')
        booking['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        before = self.storage.snapshot()
        async with self.lock:
            task = asyncio.create_task(sweep_expired_bookings(self.storage, self.lock))
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertEqual(before, self.storage.snapshot())
        self.assertEqual(await task, [booking['id']])

    async def test_active_ride_and_maintenance_lock_preserved(self):
        active = self.hold(plan_type='rental', hub_id='hub-02', resource_name='XE-052')
        self.assertTrue(self.db.start_ride(active['id'])['success'])
        held = self.hold(plan_type='rental', hub_id='hub-02', resource_name='XE-061')
        self.db.maintenance_tickets.append({'status': 'PENDING', 'device_code': 'XE-061'})
        count = self.db.get_hub('hub-02')['available_bikes']
        ids = await sweep_expired_bookings(self.storage, self.lock, datetime.now(timezone.utc) + timedelta(days=1))
        self.assertEqual(ids, [held['id']])
        self.assertEqual(self.db.user['active_services']['ride']['booking_id'], active['id'])
        self.assertEqual(self.db.get_hub('hub-02')['available_bikes'], count)
        self.assertNotEqual(next(b for b in self.db.get_hub('hub-02')['bikes'] if b['id'] == 'XE-061')['status'], 'Sẵn sàng')

    async def test_loop_survives_one_failure_and_cancels_cleanly(self):
        calls = 0
        retried = asyncio.Event()

        async def sweep(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise PersistenceError('Lỗi ghi mô phỏng')
            retried.set()
            return []

        with patch('user.expiry_worker.sweep_expired_bookings', side_effect=sweep):
            with self.assertLogs('user.expiry_worker', level='ERROR'):
                task = asyncio.create_task(run_expiry_worker(self.storage, self.lock, 0.001))
                try:
                    await asyncio.wait_for(retried.wait(), timeout=1)
                finally:
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
        self.assertGreaterEqual(calls, 2)
        self.assertTrue(task.done())

    def test_invalid_interval_rejected(self):
        for value in ('0', '-1', 'nan', 'inf', '', 'abc'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                expiry_interval(value)
        self.assertEqual(expiry_interval(), 5)


if __name__ == '__main__':
    unittest.main()
