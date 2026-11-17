// Thousands grouping (1,000,000), because the assistant's own text uses it and one message must not mix styles.
// Indian lakh grouping everywhere would need the backend text changed too (backlog U1).
const LOCALE = "en-US";
const rupees = new Intl.NumberFormat(LOCALE, { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export function inr(n: number): string {
  return rupees.format(n);
}

export function money(n: number, currency: string): string {
  try {
    return new Intl.NumberFormat(LOCALE, { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
  } catch {
    return String(Math.round(n));
  }
}

export function signedPct(n: number, digits = 1): string {
  return `${n > 0 ? "+" : ""}${n.toFixed(digits)}%`;
}

export function sign(n: number): "up" | "down" | "flat" {
  return n > 0 ? "up" : n < 0 ? "down" : "flat";
}

export function yearsAndMonths(years: number): string {
  const total = Math.round(years * 12);
  const y = Math.floor(total / 12);
  const m = total % 12;
  return [y ? `${y} yr` : "", m ? `${m} mo` : ""].filter(Boolean).join(" ") || "0 mo";
}

export const isRecord = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);
export const isNum = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);
