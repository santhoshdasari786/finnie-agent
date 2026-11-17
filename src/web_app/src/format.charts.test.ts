import { compactMoney, formatDate, price } from "./format";

describe("compactMoney (axis labels)", () => {
  it.each([
    [0, "₹0"],
    [950, "₹950"],
    [1_500, "₹1.5K"],
    [24_000, "₹24K"],
    [2_500_000, "₹2.5M"],
    [1_000_000_000, "₹1B"],
  ])("%s -> %s", (n, out) => expect(compactMoney(n, "INR")).toBe(out));

  it("keeps the sign of a negative number", () => {
    expect(compactMoney(-1500, "INR")).toBe("-₹1.5K");
  });

  it("uses the currency it is given", () => {
    expect(compactMoney(2_500_000, "USD")).toBe("$2.5M");
  });

  it("falls back to a plain number for an unknown currency", () => {
    expect(compactMoney(1234.6, "???")).toBe("1235");
  });
});

describe("formatDate", () => {
  it("writes a day, a short month and a year", () => {
    expect(formatDate("2026-08-17")).toBe("17 Aug 2026");
    expect(formatDate("2026-01-05")).toBe("5 Jan 2026");
    expect(formatDate("2026-12-31")).toBe("31 Dec 2026");
  });

  it("does not shift the day for the viewer's time zone", () => {
    expect(formatDate("2026-03-01")).toBe("1 Mar 2026");
  });

  it("reads the date part of a full timestamp", () => {
    expect(formatDate("2026-11-17T05:30:00+00:00")).toBe("17 Nov 2026");
  });

  it("returns the input when it is not a date", () => {
    expect(formatDate("soon")).toBe("soon");
    expect(formatDate("2026-13-40")).toBe("2026-13-40");
  });

  it.each(["2026-02-30", "2026-04-31", "2026-00-10", "2026-03-00"])("returns the input for the impossible date %s", (iso) => {
    expect(formatDate(iso)).toBe(iso);
  });

  it("accepts the last day of a leap February", () => {
    expect(formatDate("2028-02-29")).toBe("29 Feb 2028");
    expect(formatDate("2027-02-29")).toBe("2027-02-29");
  });
});

describe("price (two decimals, because prices are not round)", () => {
  it.each([
    [110, "INR", "₹110.00"],
    [2406.6, "INR", "₹2,406.60"],
    [25387.4, "INR", "₹25,387.40"],
    [0.5, "INR", "₹0.50"],
    [190, "USD", "$190.00"],
  ])("%s %s -> %s", (n, currency, out) => expect(price(n, currency)).toBe(out));

  it("falls back to a plain number for an unknown currency", () => {
    expect(price(12.345, "???")).toBe("12.35");
  });
});
