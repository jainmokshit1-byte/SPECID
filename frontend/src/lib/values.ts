/** A spec value for display: never invent one, show a dash when it is unknown. */
export function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}
