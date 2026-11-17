import { inr, money, signedPct, yearsAndMonths } from "./format";

describe("number formats", () => {
  it("groups rupees in thousands, the way the assistant's own text does", () => {
    expect(inr(5000000)).toBe("₹5,000,000");
    expect(inr(116395.5)).toBe("₹116,396");
    expect(inr(0)).toBe("₹0");
  });

  it("formats a quote in its own currency", () => {
    expect(money(1500.5, "INR")).toBe("₹1,501");
    expect(money(189.4, "USD")).toContain("189");
  });

  it("survives an unknown currency code", () => {
    expect(money(1500.4, "NOT-A-CODE")).toBe("1500");
  });

  it("signs percentages", () => {
    expect(signedPct(5.2)).toBe("+5.2%");
    expect(signedPct(-2.5)).toBe("-2.5%");
    expect(signedPct(0)).toBe("0.0%");
    expect(signedPct(0.456, 2)).toBe("+0.46%");
  });

  it("writes years and months", () => {
    expect(yearsAndMonths(9.25)).toBe("9 yr 3 mo");
    expect(yearsAndMonths(2)).toBe("2 yr");
    expect(yearsAndMonths(0.5)).toBe("6 mo");
    expect(yearsAndMonths(0)).toBe("0 mo");
  });
});
