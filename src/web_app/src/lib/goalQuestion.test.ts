import { buildGoalQuestion, parseAmount, problems, validateGoal, type GoalForm } from "./goalQuestion";

const empty: GoalForm = { years: "", target: "", monthly: "", start: "", risk: "", rate: "" };
const form = (over: Partial<GoalForm>): GoalForm => ({ ...empty, ...over });

describe("parseAmount", () => {
  it.each([
    ["5000000", 5_000_000],
    ["50,00,000", 5_000_000],
    ["5,000,000", 5_000_000],
    ["₹ 20,000", 20_000],
    [" 1500.5 ", 1500.5],
    ["0", 0],
  ])("%s -> %s", (raw, n) => expect(parseAmount(raw)).toBe(n));

  it.each(["", "   ", "abc", "12abc", "1e5", "-5", "Infinity", "1.2.3", "50 lakh"])("%j -> null", (raw) => {
    expect(parseAmount(raw)).toBeNull();
  });
});

describe("validateGoal", () => {
  it("accepts a full goal", () => {
    expect(validateGoal(form({ years: "10", target: "5000000", monthly: "20000" }))).toEqual([]);
  });

  it("accepts years with only a monthly amount", () => {
    expect(validateGoal(form({ years: "10", monthly: "20000" }))).toEqual([]);
  });

  it("accepts years with only a starting balance", () => {
    expect(validateGoal(form({ years: "5", start: "100000" }))).toEqual([]);
  });

  it("accepts a target with a monthly amount and no years (time to reach)", () => {
    expect(validateGoal(form({ target: "5000000", monthly: "20000" }))).toEqual([]);
  });

  it("accepts a target with a starting balance and no years", () => {
    expect(validateGoal(form({ target: "5000000", start: "100000" }))).toEqual([]);
  });

  it("needs an amount to work with", () => {
    expect(validateGoal(form({ years: "10" }))).toEqual(["Give a target amount, a monthly amount or a starting balance."]);
  });

  it("a zero monthly amount and zero balance are not an amount", () => {
    expect(validateGoal(form({ years: "10", monthly: "0", start: "0" }))).toHaveLength(1);
  });

  it("without years it needs a target and something to save from", () => {
    expect(validateGoal(form({ target: "5000000" }))[0]).toMatch(/years/i);
    expect(validateGoal(form({ monthly: "20000" }))[0]).toMatch(/years/i);
  });

  it("an empty form gives one clear message, not three", () => {
    expect(validateGoal(empty)).toHaveLength(1);
  });

  it.each(["0", "-1", "61", "abc", "10.5.1"])("years %j is rejected", (years) => {
    expect(validateGoal(form({ years, target: "5000000" }))).toContain("Years must be more than 0 and at most 60.");
  });

  it("allows part of a year and the 60 limit", () => {
    expect(validateGoal(form({ years: "7.5", monthly: "1000" }))).toEqual([]);
    expect(validateGoal(form({ years: "0.5", monthly: "1000" }))).toEqual([]);
    expect(validateGoal(form({ years: "60", monthly: "1000" }))).toEqual([]);
  });

  it("rejects a target of zero", () => {
    expect(validateGoal(form({ years: "10", target: "0", monthly: "1000" }))).toContain("The target must be more than zero.");
  });

  it.each([["monthly", "Monthly saving"], ["start", "Starting balance"], ["target", "Target amount"]] as const)(
    "rejects a %s that is not a number", (field, label) => {
      expect(validateGoal(form({ years: "10", monthly: "1000", [field]: "lots" }))).toContain(`${label} must be a number, like 20,000.`);
    });

  it("rejects a return outside 0 to 30", () => {
    expect(validateGoal(form({ years: "10", monthly: "1000", rate: "31" }))).toContain("Yearly return must be between 0 and 30.");
    expect(validateGoal(form({ years: "10", monthly: "1000", rate: "-1" }))).toContain("Yearly return must be between 0 and 30.");
    expect(validateGoal(form({ years: "10", monthly: "1000", rate: "12" }))).toEqual([]);
    expect(validateGoal(form({ years: "10", monthly: "1000", rate: "0" }))).toEqual([]);
    expect(validateGoal(form({ years: "10", monthly: "1000", rate: "30" }))).toEqual([]);
  });
});

describe("buildGoalQuestion (the same sentence the MCP tool writes)", () => {
  it("always starts a new goal, so numbers from an earlier goal are not reused", () => {
    for (const f of [form({ years: "10", monthly: "1000" }), form({ target: "5000000", monthly: "1000" }), form({ years: "5", target: "100000" })]) {
      expect(buildGoalQuestion(f).startsWith("New goal: ")).toBe(true);
    }
  });

  it("a full goal", () => {
    expect(buildGoalQuestion(form({ years: "10", target: "5,000,000", monthly: "20000", risk: "aggressive", rate: "12" })))
      .toBe("New goal: Can I reach 5000000 rupees in 10 years, saving 20000 rupees a month? My risk appetite is aggressive. Assume 12% returns.");
  });

  it("no target: what will I have", () => {
    expect(buildGoalQuestion(form({ years: "7.5", monthly: "5000" }))).toBe("New goal: What will I have in 7.5 years, saving 5000 rupees a month?");
  });

  it("a starting balance", () => {
    expect(buildGoalQuestion(form({ years: "5", start: "1,00,000" }))).toBe("New goal: What will I have in 5 years, starting with 100000 rupees?");
  });

  it("a target with a monthly amount and a balance", () => {
    expect(buildGoalQuestion(form({ years: "10", target: "5000000", monthly: "20000", start: "100000" })))
      .toBe("New goal: Can I reach 5000000 rupees in 10 years, saving 20000 rupees a month, starting with 100000 rupees?");
  });

  it("no years: how long will it take", () => {
    expect(buildGoalQuestion(form({ target: "5000000", monthly: "20000" })))
      .toBe("New goal: How long will it take to reach 5000000 rupees, saving 20000 rupees a month?");
    expect(buildGoalQuestion(form({ target: "5000000", start: "100000" })))
      .toBe("New goal: How long will it take to reach 5000000 rupees, starting with 100000 rupees?");
  });

  it("leaves out zeros and blanks", () => {
    expect(buildGoalQuestion(form({ years: "10", target: "5000000", monthly: "0", start: "0" }))).toBe("New goal: Can I reach 5000000 rupees in 10 years?");
  });

  it("says '1 year', not '1 years'", () => {
    expect(buildGoalQuestion(form({ years: "1", monthly: "1000" }))).toBe("New goal: What will I have in 1 year, saving 1000 rupees a month?");
  });

  it("rounds an amount to whole rupees", () => {
    expect(buildGoalQuestion(form({ years: "2", monthly: "1500.6" }))).toContain("saving 1501 rupees a month");
  });

  it("a rate of zero is still a stated assumption", () => {
    expect(buildGoalQuestion(form({ years: "10", monthly: "1000", rate: "0" }))).toContain("Assume 0% returns.");
  });

  it("prints big numbers in full, never as 5e+6", () => {
    expect(buildGoalQuestion(form({ years: "10", target: "5000000", monthly: "1000" }))).not.toMatch(/e\+/);
  });
});

describe("problems (which field is wrong)", () => {
  it("names the field for a bad number", () => {
    const found = problems(form({ years: "99", monthly: "lots", start: "x", target: "y", rate: "50" }));
    expect(found.map((p) => p.field).sort()).toEqual(["monthly", "rate", "start", "target", "years"]);
  });

  it("names years when only the time is missing", () => {
    expect(problems(form({ target: "5000000" }))).toEqual([{ field: "years", message: expect.stringMatching(/years/i) }]);
  });

  it("has no field for 'give an amount'", () => {
    expect(problems(form({ years: "10" }))).toEqual([{ field: null, message: "Give a target amount, a monthly amount or a starting balance." }]);
  });

  it("validateGoal is just the messages", () => {
    const f = form({ years: "99", monthly: "lots" });
    expect(validateGoal(f)).toEqual(problems(f).map((p) => p.message));
  });
});
