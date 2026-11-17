export interface GoalForm {
  years: string;
  target: string;
  monthly: string;
  start: string;
  risk: string;
  rate: string;
}

export type Field = keyof GoalForm;
export interface Problem {
  field: Field | null;
  message: string;
}

/** "50,00,000" or "₹ 20,000" -> a number. Anything else (words, signs, exponents) is null. */
export function parseAmount(raw: string): number | null {
  const s = raw.replace(/[₹,\s]/g, "");
  return /^\d+(\.\d+)?$/.test(s) ? Number(s) : null;
}

const AMOUNTS: [Field, string][] = [["target", "Target amount"], ["monthly", "Monthly saving"], ["start", "Starting balance"]];

export function problems(form: GoalForm): Problem[] {
  const found: Problem[] = [];
  const text = (f: Field) => form[f].trim();
  const num = (f: Field) => (text(f) === "" ? null : parseAmount(text(f)));

  if (text("years") !== "") {
    const y = num("years");
    if (y === null || y <= 0 || y > 60) found.push({ field: "years", message: "Years must be more than 0 and at most 60." });
  }
  for (const [field, label] of AMOUNTS) {
    if (text(field) !== "" && num(field) === null) found.push({ field, message: `${label} must be a number, like 20,000.` });
  }
  if (num("target") === 0) found.push({ field: "target", message: "The target must be more than zero." });
  if (text("rate") !== "") {
    const r = num("rate");
    if (r === null || r > 30) found.push({ field: "rate", message: "Yearly return must be between 0 and 30." });
  }
  if (found.length) return found;

  const target = num("target") ?? 0;
  const monthly = num("monthly") ?? 0;
  const start = num("start") ?? 0;
  if (text("years") === "") {
    const canSolveForTime = target > 0 && (monthly > 0 || start > 0);
    return canSolveForTime ? [] : [{
      field: "years",
      message: "Enter the years, or give a target plus a monthly amount (or a starting balance) to find how long it takes.",
    }];
  }
  if (!(target > 0 || monthly > 0 || start > 0)) {
    return [{ field: null, message: "Give a target amount, a monthly amount or a starting balance." }];
  }
  return [];
}

export const validateGoal = (form: GoalForm): string[] => problems(form).map((p) => p.message);

/** The sentence a person would say. Same wording as the MCP tool, so the goal agent reads it the same way. */
export function buildGoalQuestion(form: GoalForm): string {
  const years = parseAmount(form.years);
  const target = parseAmount(form.target) ?? 0;
  const monthly = parseAmount(form.monthly) ?? 0;
  const start = parseAmount(form.start) ?? 0;
  const rate = parseAmount(form.rate);
  const rupees = (n: number) => `${n.toFixed(0)} rupees`;

  let head: string;
  if (years === null) head = `How long will it take to reach ${rupees(target)}`;
  else {
    const span = `${years} ${years === 1 ? "year" : "years"}`;
    head = target > 0 ? `Can I reach ${rupees(target)} in ${span}` : `What will I have in ${span}`;
  }
  if (monthly > 0) head += `, saving ${rupees(monthly)} a month`;
  if (start > 0) head += `, starting with ${rupees(start)}`;

  const parts = [`New goal: ${head}?`];
  if (form.risk) parts.push(`My risk appetite is ${form.risk}.`);
  if (rate !== null) parts.push(`Assume ${rate}% returns.`);
  return parts.join(" ");
}
