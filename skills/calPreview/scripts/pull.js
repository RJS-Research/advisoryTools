#!/usr/bin/env osascript -l JavaScript
// Local-iCal pull via EventKit through the JXA ObjC bridge.
// No compile, no install, no shipped binary — runs on any Mac.
// Usage: osascript -l JavaScript pull.js <startISOdate> <endISOdate>
//   dates are YYYY-MM-DD (local tz); end is exclusive.
ObjC.import('EventKit');
ObjC.import('Foundation');
ObjC.import('stdlib');   // for $.exit

function run(argv) {
  const startStr = argv[0] || '2026-07-13';
  const endStr   = argv[1] || '2026-07-20';

  const store = $.EKEventStore.alloc.init;

  function err(msg) {
    $.NSFileHandle.fileHandleWithStandardError.writeData(
      $.NSString.alloc.initWithUTF8String(msg + '\n')
        .dataUsingEncoding($.NSUTF8StringEncoding));
  }

  // --- permission: trust authorizationStatus; ask whenever we can still win ---
  // 0 notDetermined · 2 denied/restricted · 3 fullAccess (macOS 14+) · 4 writeOnly
  //
  // macOS 14 split Calendar access into full vs write-only, and the legacy
  // requestAccessToEntityType: call grants WRITE-ONLY there — status 4, which
  // reads no events and makes this script useless. So full access has to be
  // asked for by name. The JXA selector is requestFullAccessToEvents*With*
  // Completion; drop the "With" and the property is simply undefined, the
  // legacy branch is taken on every modern Mac, and the grant silently comes
  // back write-only. That typo is what broke clean-room pass #3.
  //
  // Write-only is also upgradable: EventKit lets an app holding it ask for
  // full access, so status 4 re-asks rather than dead-ending.
  let status = Number($.EKEventStore.authorizationStatusForEntityType($.EKEntityTypeEvent));
  if (status === 0 || status === 4) {
    let done = false;
    const cb = function () { done = true; };            // re-read status after, don't trust the bool
    if (typeof store.requestFullAccessToEventsWithCompletion === 'function') {
      store.requestFullAccessToEventsWithCompletion(cb);        // macOS 14+
    } else if (status === 0) {
      store.requestAccessToEntityTypeCompletion($.EKEntityTypeEvent, cb);  // pre-macOS 14
    } else {
      done = true;      // writeOnly with no full-access API: nothing left to ask
    }
    const deadline = $.NSDate.dateWithTimeIntervalSinceNow(60);
    while (!done && $.NSDate.date.compare(deadline) === -1) {
      $.NSRunLoop.currentRunLoop.runModeBeforeDate(
        $.NSDefaultRunLoopMode, $.NSDate.dateWithTimeIntervalSinceNow(0.05));
    }
    status = Number($.EKEventStore.authorizationStatusForEntityType($.EKEntityTypeEvent));
  }
  if (status !== 3) {
    if (status === 4) {
      err('DENIED: only WRITE-ONLY calendar access is granted (status=4). This ' +
          'tool reads events, so it needs Full Access. Open System Settings > ' +
          'Privacy & Security > Calendars, switch the app running this OFF and ' +
          'back ON, and choose "Full Access" when asked. Then retry.');
    } else {
      err('DENIED: Calendar access not granted (status=' + status + '). ' +
          'Enable it in System Settings > Privacy & Security > Calendars for the app running this, then retry.');
    }
    $.exit(2);
  }

  // --- build [start,end) in the system calendar/timezone ---
  const cal = $.NSCalendar.currentCalendar;
  function midnight(s) {
    const c = $.NSDateComponents.alloc.init;
    c.year = parseInt(s.slice(0, 4), 10);
    c.month = parseInt(s.slice(5, 7), 10);
    c.day = parseInt(s.slice(8, 10), 10);
    return cal.dateFromComponents(c);
  }
  const start = midnight(startStr), end = midnight(endStr);

  const pred = store.predicateForEventsWithStartDateEndDateCalendars(start, end, $());
  const events = store.eventsMatchingPredicate(pred);

  const iso = $.NSISO8601DateFormatter.alloc.init;
  iso.timeZone = $.NSTimeZone.localTimeZone;   // emit local wall-clock + offset, not UTC
  const rows = [];
  const n = events.count;
  for (let i = 0; i < n; i++) {
    const e = events.objectAtIndex(i);
    rows.push({
      calendar: ObjC.unwrap(e.calendar.title),
      title: e.title ? ObjC.unwrap(e.title) : '(untitled)',
      start: ObjC.unwrap(iso.stringFromDate(e.startDate)),
      end: ObjC.unwrap(iso.stringFromDate(e.endDate)),
      allDay: e.isAllDay ? true : false,
    });
  }
  $.NSFileHandle.fileHandleWithStandardError.writeData(
    $.NSString.alloc.initWithUTF8String('events=' + rows.length + '\n')
      .dataUsingEncoding($.NSUTF8StringEncoding));
  return JSON.stringify(rows);
}
