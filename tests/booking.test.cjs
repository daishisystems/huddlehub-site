const test = require('node:test');
const assert = require('node:assert/strict');
const booking = require('../public/assets/js/booking.js');

function validBooking(children) {
  return {
    parent: '  Alex Parent  ', phone: '076 824 3254', email: '', message: '',
    children: children || [{ name: 'Taylor', age: '8', groups: ['tue1-hk'] }]
  };
}

test('exact Term 4 timetable contains every supplied group', () => {
  assert.equal(booking.GROUPS.length, 12);
  assert.equal(new Set(booking.GROUPS.map(group => group.id)).size, 12);
  assert.deepEqual(booking.GROUPS.filter(group => group.day === 'Wed').map(group => [group.sport, group.who, group.ages]), [
    ['Soccer', 'Girls', 'All ages 6–13'], ['Rugby', 'Boys', 'All ages 6–13']
  ]);
  assert.deepEqual(booking.GROUPS.filter(group => group.sport === 'Performance Lab').map(group => [group.day, group.time]), [
    ['Thu', '14:30–15:30'], ['Thu', '15:30–16:30']
  ]);
});

test('South African local and international formats normalize consistently', () => {
  for (const number of ['076 824 3254', '(076) 824-3254', '+27 76 824 3254', '0027768243254', '27768243254']) {
    assert.equal(booking.normalizePhone(number), '+27768243254');
  }
  for (const number of ['', '076824325', '07682432545', '+44768243254', 'text0768243254', '0968243254']) {
    assert.equal(booking.normalizePhone(number), null);
  }
});

test('a second simultaneous group is rejected without altering the first', () => {
  const selection = ['thu1-hk'];
  const result = booking.toggleSelection(selection, 'thu1-pl');
  assert.deepEqual(result.groups, ['thu1-hk']);
  assert.match(result.error, /Thursday.*14:30–15:30.*Remove Hockey/);
  assert.deepEqual(selection, ['thu1-hk']);
  assert.deepEqual(booking.toggleSelection(selection, 'thu1-hk'), { groups: [], error: '' });
});

test('adjacent sessions and Tue/Thu hockey do not conflict', () => {
  assert.equal(booking.groupsOverlap({ day: 'Tue', time: '14:30–15:30' }, { day: 'Tue', time: '15:30–16:30' }), false);
  assert.equal(booking.groupsOverlap({ day: 'Tue', time: '14:30–15:30' }, { day: 'Tue', time: '15:15–16:30' }), true);
  assert.deepEqual(booking.toggleSelection(['tue1-hk'], 'thu1-hk'), { groups: ['tue1-hk', 'thu1-hk'], error: '' });
  assert.deepEqual(booking.toggleSelection(['thu1-hk'], 'thu2-pl'), { groups: ['thu1-hk', 'thu2-pl'], error: '' });
});

test('siblings can share a slot but every child requires name, integer age and group', () => {
  const siblings = [{ name: 'Taylor', age: '8', groups: ['tue1-hk'] }, { name: 'Jamie', age: '7', groups: ['tue1-nb'] }];
  assert.equal(booking.validateBooking(validBooking(siblings)), null);
  const missingChild = [...siblings, { name: '', age: '', groups: [] }];
  assert.deepEqual(booking.validateBooking(validBooking(missingChild)), { field: 'name', childIndex: 2, message: "Please add Child 3's name." });
  assert.equal(booking.validateBooking(validBooking([{ name: 'Jamie', age: '7', groups: [] }])).field, 'groups');
  for (const age of ['', '5', '14', '6.5', '7years', '-8']) {
    assert.equal(booking.validateBooking(validBooking([{ name: 'Taylor', age, groups: ['tue1-hk'] }])).field, 'age');
  }
  for (const age of ['6', '13']) {
    assert.equal(booking.validateBooking(validBooking([{ name: 'Taylor', age, groups: ['tue2-hk'] }])), null);
  }
});

test('submit validation catches invalid, unknown and conflicting bookings', () => {
  assert.equal(booking.validateBooking({ ...validBooking(), parent: ' ' }).field, 'parent-name');
  assert.equal(booking.validateBooking({ ...validBooking(), phone: '+44768243254' }).field, 'phone');
  assert.equal(booking.validateBooking({ ...validBooking(), email: 'parent@' }).field, 'email');
  assert.equal(booking.validateBooking({ ...validBooking(), email: 'parent@example.com' }), null);
  assert.equal(booking.validateBooking(validBooking([{ name: 'Taylor', age: '8', groups: ['tue1-hk', 'tue1-nb'] }])).field, 'groups');
  assert.equal(booking.validateBooking(validBooking([{ name: 'Taylor', age: '8', groups: ['unknown'] }])).field, 'groups');
});

test('Netlify payload and WhatsApp text preserve all children, groups and special characters', () => {
  const details = validBooking([
    { name: 'Ava & Ben <test>', age: '8', groups: ['tue1-hk', 'thu1-hk'] },
    { name: 'Jamie', age: '12', groups: ['fri2-sc'] }
  ]);
  details.email = 'alex+term4@example.com';
  details.message = 'Can we pay half now? & later = yes';
  const payload = booking.bookingPayload(details, 'term4-registration', '');
  const decoded = new URLSearchParams(payload.toString());
  assert.equal(decoded.get('form-name'), 'term4-registration');
  assert.equal(decoded.get('parent-name'), 'Alex Parent');
  assert.equal(decoded.get('phone'), '+27768243254');
  assert.equal(decoded.get('email'), details.email);
  assert.equal(decoded.get('message'), details.message);
  assert.equal(decoded.get('bot-field'), '');
  assert.equal(decoded.get('children-and-groups'), 'Ava & Ben <test>, age 8\n  - Tue 14:30–15:30 Hockey Mixed (U7 & U9)\n  - Thu 14:30–15:30 Hockey Mixed (U7 & U9)\n\nJamie, age 12\n  - Fri 15:30–16:30 Soccer Boys (U11 & U13)');
  const whatsapp = new URL(booking.whatsappUrl(details));
  assert.equal(whatsapp.hostname, 'wa.me');
  assert.equal(whatsapp.pathname, '/27768243254');
  assert.match(whatsapp.searchParams.get('text'), /Ava & Ben <test>.*age 8/);
  assert.match(whatsapp.searchParams.get('text'), /Notes: Can we pay half now\? & later = yes/);
});

test('preview behavior is limited to loopback hostnames', () => {
  for (const host of ['localhost', '127.0.0.1', '[::1]', '::1']) assert.equal(booking.isLocalHostname(host), true);
  for (const host of ['www.huddlehub.co.za', 'huddlehub.co.za', 'localhost.example.com']) assert.equal(booking.isLocalHostname(host), false);
});
