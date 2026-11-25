/** Kiểm tra đồng hồ chuyến đi bằng thời gian giả, không gọi API thật. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
function run() {
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { innerText: '' });
    return nodes.get(id);
  };
  const state = { activeServices: { ride: null }, activeRide: null };
  const timers = new Map();
  let counter = 0;
  const ctx = { AppState: state, document: { getElementById: node },
    setInterval: (fn, ms) => { assert.equal(ms, 1000); timers.set(++counter, fn); return counter; },
    clearInterval: id => timers.delete(id) };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../js/modules/active-services.js'), 'utf8'), ctx);
  const app = ctx.UserModules.ActiveServices;
  const start = Date.parse('2026-11-26T01:00:00Z');
  state.activeServices.ride = { trip_id: 'A', billing_started_at: new Date(start).toISOString(),
    started_at: new Date(start + 30000).toISOString(), elapsed_minutes: 0 };
  app.updateRideClock(start + 65000);
  assert.equal(node('rideTimer').innerText, '1 phút 05 giây');
  assert.notEqual(node('rideBookedAt').innerText, '—');
  assert.notEqual(node('rideStartedAt').innerText, '—');
  app.updateRideClock(start + 301000); // Tab ngủ rồi mở lại phải nhảy tới thời gian thực.
  assert.equal(node('rideTimer').innerText, '5 phút 01 giây');
  state.activeServices.ride = { trip_id: 'B', started_at: new Date(start + 300000).toISOString() };
  app.updateRideClock(start + 301000);
  assert.equal(node('rideTimer').innerText, '0 phút 01 giây');
  state.activeServices.ride = { trip_id: 'LEGACY', elapsed_minutes: 13 };
  app.updateRideClock(start);
  assert.equal(node('rideTimer').innerText, '13 phút (dữ liệu mẫu)');
  assert.equal(node('rideBookedAt').innerText, '—');
  assert.equal(node('rideStartedAt').innerText, '—');
  state.activeServices.ride = null;
  app.updateRideClock(start);
  assert.equal(node('rideTimer').innerText, '—');
  app.startRideTicker(); app.startRideTicker();
  assert.equal(timers.size, 1);
  return { passed: 6 };
}
module.exports = { run };
if (require.main === module) console.log(run());
