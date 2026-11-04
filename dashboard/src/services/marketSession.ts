// US market session shown in Bangkok time. Everything is derived from the IANA time zones through
// Intl, so US daylight saving is handled by the tz database rather than a hard-coded ICT offset.
// Exchange holidays are NOT modelled here: there is no verified US calendar in ACASH yet, and a
// guessed holiday would silently mislabel a trading day, so the view says so explicitly.

export const NEW_YORK = 'America/New_York';
export const BANGKOK = 'Asia/Bangkok';

export interface SessionMoment { at_ny: string; at_bangkok: string }
export interface NextChange extends SessionMoment { kind: 'OPEN' | 'CLOSE' }
export interface MarketSessionView {
  state: 'OPEN' | 'CLOSED';
  new_york_time: string;
  bangkok_time: string;
  next_change: NextChange | null;
  calendar: 'US_HOLIDAYS_NOT_VERIFIED';
}

const parts = (date: Date, timeZone: string): Record<string, number> => {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone, hour12: false, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', weekday: 'short',
  });
  const out: Record<string, number> = {};
  for (const part of formatter.formatToParts(date)) {
    if (part.type === 'literal') continue;
    if (part.type === 'weekday') { out.weekday = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(part.value); continue; }
    out[part.type] = Number(part.value);
  }
  out.hour = out.hour % 24;
  return out;
};

const offsetMinutes = (date: Date): number => {
  const p = parts(date, NEW_YORK);
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
  return (asUtc - date.getTime()) / 60000;
};

const nyWallClock = (year: number, month: number, day: number, hour: number, minute: number): Date => {
  const guess = Date.UTC(year, month - 1, day, hour, minute);
  return new Date(guess - offsetMinutes(new Date(guess)) * 60000);
};

const clock = (date: Date, timeZone: string): string => {
  const p = parts(date, timeZone);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(p.hour)}:${pad(p.minute)}`;
};

const dayKey = (date: Date): string => {
  const p = parts(date, NEW_YORK);
  return `${p.year}-${String(p.month).padStart(2, '0')}-${String(p.day).padStart(2, '0')}`;
};

const ictLabel = (date: Date): string => {
  const p = parts(date, BANGKOK);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${p.year}-${pad(p.month)}-${pad(p.day)} ${pad(p.hour)}:${pad(p.minute)} ICT`;
};

const nyLabel = (date: Date): string => {
  const p = parts(date, NEW_YORK);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${p.year}-${pad(p.month)}-${pad(p.day)} ${pad(p.hour)}:${pad(p.minute)} ET`;
};

const isWeekday = (weekday: number): boolean => weekday >= 1 && weekday <= 5;

export function marketSession(now: Date = new Date()): MarketSessionView {
  const ny = parts(now, NEW_YORK);
  const minutes = ny.hour * 60 + ny.minute;
  const open = isWeekday(ny.weekday) && minutes >= 570 && minutes < 960;
  let next: { kind: 'OPEN' | 'CLOSE'; at: Date } | null = null;
  if (open) {
    next = { kind: 'CLOSE', at: nyWallClock(ny.year, ny.month, ny.day, 16, 0) };
  } else {
    next = { kind: 'OPEN', at: nyWallClock(ny.year, ny.month, ny.day, 9, 30) };
    for (let offset = 0; offset < 8 && next.at.getTime() <= now.getTime(); offset += 1) {
      const candidate = new Date(next.at.getTime() + 86400000);
      const cp = parts(candidate, NEW_YORK);
      next = { kind: 'OPEN', at: nyWallClock(cp.year, cp.month, cp.day, 9, 30) };
    }
    // Skip a weekend landing: walk forward until the candidate is a New York weekday.
    for (let guard = 0; guard < 10; guard += 1) {
      const cp = parts(next.at, NEW_YORK);
      if (isWeekday(cp.weekday)) break;
      const following = new Date(next.at.getTime() + 86400000);
      const fp = parts(following, NEW_YORK);
      next = { kind: 'OPEN', at: nyWallClock(fp.year, fp.month, fp.day, 9, 30) };
    }
  }
  return {
    state: open ? 'OPEN' : 'CLOSED',
    new_york_time: clock(now, NEW_YORK),
    bangkok_time: clock(now, BANGKOK),
    next_change: next ? { kind: next.kind, at_ny: nyLabel(next.at), at_bangkok: ictLabel(next.at) } : null,
    calendar: 'US_HOLIDAYS_NOT_VERIFIED',
  };
}

export const sessionKey = dayKey;
