import { render, screen, within } from "@testing-library/react";
import { DataPanel } from "./DataPanel";

const scenario = (name: string, rate: number, projected: number | null, gap: number | null, need: number | null, years: number | null) =>
  ({ name, annual_rate_pct: rate, projected, gap, required_monthly: need, years_needed: years });

const goal = (scenarios: unknown[], over: object = {}) => ({
  plan: { years: 10, monthly: 20000, start: 0, target: 5000000, risk: "moderate", already_met: false, scenarios, ...over },
});

describe("DataPanel: goal plan", () => {
  const data = goal([
    scenario("pessimistic", 3, 2794828, -2205172, 71561, null),
    scenario("expected", 7, 3461696, -1538304, 57775, null),
    scenario("optimistic", 11, 5339963, 339963, 46083, null),
  ]);

  it("shows a row per scenario with its rate", () => {
    render(<DataPanel data={data} />);
    expect(screen.getAllByRole("row")).toHaveLength(4);
    expect(screen.getByRole("row", { name: /Pessimistic/ })).toHaveTextContent("3%");
    expect(screen.getByRole("row", { name: /Optimistic/ })).toHaveTextContent("11%");
  });

  it("formats rupees the way the reply text above it does", () => {
    render(<DataPanel data={data} />);
    expect(screen.getByText("₹2,794,828")).toBeInTheDocument();
  });

  it("says short by or ahead by", () => {
    render(<DataPanel data={data} />);
    expect(screen.getByText("short by ₹2,205,172")).toBeInTheDocument();
    expect(screen.getByText("ahead by ₹339,963")).toBeInTheDocument();
  });

  it("shows the monthly amount needed when there is a target", () => {
    render(<DataPanel data={data} />);
    expect(screen.getByText("₹57,775")).toBeInTheDocument();
  });

  it("shows time to reach in years and months when the horizon was unknown", () => {
    render(<DataPanel data={goal([scenario("expected", 7, null, null, null, 9.25)], { years: null })} />);
    expect(screen.getByText("9 yr 3 mo")).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: /projected/i })).toBeNull();
  });

  it("says a goal cannot be reached within the limit", () => {
    render(<DataPanel data={goal([scenario("expected", 7, null, null, null, null)], { years: null })} />);
    expect(screen.getByText(/60\+ years/)).toBeInTheDocument();
  });

  it("hides a column that has no values", () => {
    render(<DataPanel data={goal([scenario("expected", 7, 1000, null, null, null)], { target: null })} />);
    expect(screen.queryByRole("columnheader", { name: /needed/i })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: /vs target/i })).toBeNull();
  });

  it("says what it assumed", () => {
    render(<DataPanel data={data} />);
    expect(screen.getByText(/10 years/)).toBeInTheDocument();
    expect(screen.getByText(/₹20,000 a month/)).toBeInTheDocument();
    expect(screen.getByText(/illustrative/i)).toBeInTheDocument();
  });

  it("does not crash on a malformed plan", () => {
    const { container } = render(<DataPanel data={{ plan: { scenarios: "oops" } }} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("DataPanel: portfolio", () => {
  const metrics = {
    total_value: 116395.5,
    holdings: [
      { symbol: "RELIANCE", quantity: 10, price: 1500, value: 15000, allocation_pct: 12.89, pnl_pct: 5.2 },
      { symbol: "TCS", quantity: 5, price: 3000, value: 15000, allocation_pct: 12.89, pnl_pct: -2.5 },
      { symbol: "GOLDBEES", quantity: 100, price: 60, value: 6000, allocation_pct: 5.15, pnl_pct: null },
    ],
    by_asset_class: { equity: 70.5, gold: 29.5 },
    top_holding_pct: 12.89, diversification_score: 0.78, risk_assessment: "moderate", unpriced: [], unclassified: [],
  };

  it("shows the total and a row per holding", () => {
    render(<DataPanel data={{ metrics, sources: ["sample"] }} />);
    expect(screen.getByText("₹116,396")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /RELIANCE/ })).toHaveTextContent("12.9%");
  });

  it("marks gains and losses", () => {
    render(<DataPanel data={{ metrics }} />);
    expect(screen.getByText("+5.2%")).toHaveAttribute("data-sign", "up");
    expect(screen.getByText("-2.5%")).toHaveAttribute("data-sign", "down");
  });

  it("shows a dash when there is no profit figure", () => {
    render(<DataPanel data={{ metrics }} />);
    expect(within(screen.getByRole("row", { name: /GOLDBEES/ })).getByText("—")).toBeInTheDocument();
  });

  it("shows the asset classes, diversification and risk", () => {
    render(<DataPanel data={{ metrics }} />);
    expect(screen.getByText(/equity/i)).toBeInTheDocument();
    expect(screen.getByText(/70\.5%/)).toBeInTheDocument();
    expect(screen.getByText(/0\.78/)).toBeInTheDocument();
    expect(screen.getByText(/moderate/i)).toBeInTheDocument();
  });

  it("names holdings that could not be priced", () => {
    render(<DataPanel data={{ metrics: { ...metrics, unpriced: ["XYZ"] } }} />);
    expect(screen.getByText(/XYZ/)).toBeInTheDocument();
  });

  it("labels demo data", () => {
    render(<DataPanel data={{ metrics, sources: ["sample"] }} />);
    expect(screen.getByText(/demo data/i)).toBeInTheDocument();
  });

  it("does not crash on a malformed portfolio", () => {
    const { container } = render(<DataPanel data={{ metrics: { holdings: 5 } }} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("DataPanel: quotes", () => {
  const quote = (symbol: string, price: number, change: number | null, stale = false) => ({
    instrument: { symbol, exchange: "NSE" }, price, change_pct: change, currency: "INR",
    as_of: "2026-11-16T04:00:00Z", source: "yfinance", stale,
  });

  it("shows a row per quote with price and change", () => {
    render(<DataPanel data={{ quotes: [quote("RELIANCE", 1500.5, 0.45), quote("TCS", 3000, -1.2)], missing: [] }} />);
    expect(screen.getByRole("row", { name: /RELIANCE/ })).toHaveTextContent("₹1,501");
    expect(screen.getByText("+0.45%")).toHaveAttribute("data-sign", "up");
    expect(screen.getByText("-1.20%")).toHaveAttribute("data-sign", "down");
  });

  it("marks stale prices and shows the source", () => {
    render(<DataPanel data={{ quotes: [quote("RELIANCE", 1500, 0.1, true)], missing: [] }} />);
    expect(screen.getByText(/stale/i)).toBeInTheDocument();
    expect(screen.getByText(/yfinance/)).toBeInTheDocument();
  });

  it("names symbols with no price", () => {
    render(<DataPanel data={{ quotes: [quote("TCS", 3000, 0)], missing: ["NOPEXYZ"] }} />);
    expect(screen.getByText(/NOPEXYZ/)).toBeInTheDocument();
  });

  it("shows a dash for an unknown change", () => {
    render(<DataPanel data={{ quotes: [quote("TCS", 3000, null)], missing: [] }} />);
    expect(within(screen.getByRole("row", { name: /TCS/ })).getByText("—")).toBeInTheDocument();
  });
});

describe("DataPanel: anything else", () => {
  it.each([null, {}, { options: [] }, { topic: "Infosys", days: 7, clusters: [] }, { login_url: "https://x" }])("renders nothing for %j", (data) => {
    const { container } = render(<DataPanel data={data as Record<string, unknown> | null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("DataPanel: goal plan headers", () => {
  it("shows every column that has values", () => {
    const data = { plan: { years: 10, monthly: 20000, start: 0, target: 5000000, risk: "moderate", scenarios: [
      { name: "expected", annual_rate_pct: 7, projected: 3461696, gap: -1538304, required_monthly: 57775, years_needed: null }] } };
    render(<DataPanel data={data} />);
    for (const name of [/scenario/i, /return/i, /projected/i, /vs target/i, /needed per month/i]) {
      expect(screen.getByRole("columnheader", { name })).toBeInTheDocument();
    }
    expect(screen.queryByRole("columnheader", { name: /time to reach/i })).toBeNull();
  });

  it("shows the time column only when the horizon was unknown", () => {
    const data = { plan: { years: null, monthly: 10000, start: 0, target: 1000000, risk: "moderate", scenarios: [
      { name: "expected", annual_rate_pct: 7, projected: null, gap: null, required_monthly: null, years_needed: 5 }] } };
    render(<DataPanel data={data} />);
    expect(screen.getByRole("columnheader", { name: /time to reach/i })).toBeInTheDocument();
  });
});

describe("DataPanel: the needed-per-month answer", () => {
  const needed = (over: object = {}) => ({ plan: { years: 10, monthly: 0, start: 0, target: 10000000, risk: "moderate", scenarios: [
    { name: "pessimistic", annual_rate_pct: 3, projected: 0, gap: -10000000, required_monthly: 71561, years_needed: null },
    { name: "expected", annual_rate_pct: 7, projected: 0, gap: -10000000, required_monthly: 57775, years_needed: null },
  ], ...over } });

  it("shows only what is needed each month, not a meaningless projection of nothing", () => {
    render(<DataPanel data={needed()} />);
    expect(screen.getByRole("columnheader", { name: /needed per month/i })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: /projected/i })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: /vs target/i })).toBeNull();
    expect(screen.getByText("₹71,561")).toBeInTheDocument();
    expect(screen.queryByText("₹0")).toBeNull();
  });

  it("does the same when only a starting balance was given", () => {
    render(<DataPanel data={needed({ start: 500000 })} />);
    expect(screen.queryByRole("columnheader", { name: /projected/i })).toBeNull();
  });

  it("shows the projection again once a monthly amount is given", () => {
    render(<DataPanel data={needed({ monthly: 20000 })} />);
    expect(screen.getByRole("columnheader", { name: /projected/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /vs target/i })).toBeInTheDocument();
  });

  it("keeps the projection when there is no target to need anything for", () => {
    const data = { plan: { years: 10, monthly: 0, start: 500000, target: null, risk: "moderate", scenarios: [
      { name: "expected", annual_rate_pct: 7, projected: 1004831, gap: null, required_monthly: null, years_needed: null }] } };
    render(<DataPanel data={data} />);
    expect(screen.getByRole("columnheader", { name: /projected/i })).toBeInTheDocument();
  });
});
