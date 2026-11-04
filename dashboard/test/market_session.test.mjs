import test from 'node:test';
import assert from 'node:assert/strict';
import { marketSession } from '../src/services/marketSession.ts';

// Bangkok is UTC+7 all year; New York shifts between EST (UTC-5) and EDT (UTC-4). These cases pin
// the conversion so a fixed "21:30 ICT" assumption cannot creep back in.

test('regular session on a standard-time day is open', () => {
  // 2026-11-04 15:00 UTC = 10:00 EST (DST ended 2026-11-01).
  const view = marketSession(new Date('2026-11-04T15:00:00Z'));
  assert.equal(view.state, 'OPEN');
  assert.equal(view.new_york_time, '10:00');
  assert.equal(view.bangkok_time, '22:00');
  assert.equal(view.next_change.kind, 'CLOSE');
  assert.equal(view.next_change.at_bangkok, '2026-11-05 04:00 ICT');
});

test('pre-open on a daylight-time day waits for the 09:30 New York open', () => {
  // 2026-06-01 13:00 UTC = 09:00 EDT.
  const view = marketSession(new Date('2026-06-01T13:00:00Z'));
  assert.equal(view.state, 'CLOSED');
  assert.equal(view.next_change.kind, 'OPEN');
  assert.equal(view.next_change.at_bangkok, '2026-06-01 20:30 ICT');
});

test('after the close the next open is the following trading day', () => {
  // 2026-11-04 22:00 UTC = 17:00 EST, after the 16:00 close.
  const view = marketSession(new Date('2026-11-04T22:00:00Z'));
  assert.equal(view.state, 'CLOSED');
  assert.equal(view.next_change.at_ny, '2026-11-05 09:30 ET');
  assert.equal(view.next_change.at_bangkok, '2026-11-05 21:30 ICT');
});

test('a weekend never produces a Saturday or Sunday open', () => {
  // 2026-11-07 is a Saturday; 12:00 UTC = 07:00 EST.
  const view = marketSession(new Date('2026-11-07T12:00:00Z'));
  assert.equal(view.state, 'CLOSED');
  assert.equal(view.next_change.at_ny, '2026-11-09 09:30 ET');
  assert.equal(view.calendar, 'US_HOLIDAYS_NOT_VERIFIED');
});

test('holidays are explicitly not modelled rather than guessed', () => {
  // 2026-12-25 is a US holiday; without a verified calendar the view must still say so.
  const view = marketSession(new Date('2026-12-25T15:00:00Z'));
  assert.equal(view.calendar, 'US_HOLIDAYS_NOT_VERIFIED');
});
