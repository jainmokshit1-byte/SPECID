// Microcopy formats from UI/UX brief 5: dates stored UTC, shown in IST as "03 Oct 2026, 10:19";
// counts with separators ("12,345").

const IST = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Kolkata",
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function formatDateTime(iso: string): string {
  const parts = Object.fromEntries(IST.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${parts.day} ${parts.month} ${parts.year}, ${parts.hour}:${parts.minute}`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

/** A calendar day picked in IST, as the ISO instant where it starts (for `since`/`until`). */
export function istDayStart(day: string, addDays = 0): string {
  const d = new Date(`${day}T00:00:00+05:30`);
  d.setUTCDate(d.getUTCDate() + addDays);
  return d.toISOString();
}
