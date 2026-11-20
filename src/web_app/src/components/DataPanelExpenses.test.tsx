import { render, screen, within } from "@testing-library/react";
import { portfolioData } from "../test/factories";
import { DataPanel } from "./DataPanel";

function withFees(over: Record<string, unknown> = {}, sources: string[] = ["broker"]) {
  const base = portfolioData();
  const holdings = [
    { symbol: "TCS", quantity: 10, price: 3000, value: 300_000, allocation_pct: 30, pnl_pct: 12.5, expense_ratio_pct: null },
    { symbol: "NIFTYBEES", quantity: 20, price: 1500, value: 300_000, allocation_pct: 30, pnl_pct: -3.2, expense_ratio_pct: 0.05 },
    { symbol: "GOLDBEES", quantity: 100, price: 400, value: 400_000, allocation_pct: 40, pnl_pct: null, expense_ratio_pct: 0.8 },
  ];
  return {
    ...base, sources,
    metrics: { ...base.metrics, holdings, weighted_expense_ratio_pct: 0.46, annual_fund_cost: 3350, expense_covered_pct: 70, expense_unknown: [], ...over },
  };
}

const panel = () => screen.getByRole("region", { name: "Portfolio details" });

describe("DataPanel: expense ratios", () => {
  it("adds a Fee column when any holding has a ratio", () => {
    render(<DataPanel data={withFees()} />);
    expect(within(panel()).getByRole("columnheader", { name: "Fee" })).toBeInTheDocument();
    expect(within(panel()).getByText("0.80%")).toBeInTheDocument();
    expect(within(panel()).getByText("0.05%")).toBeInTheDocument();
  });

  it("shows a dash for a holding without a ratio", () => {
    render(<DataPanel data={withFees()} />);
    const row = within(panel()).getByRole("row", { name: /TCS/ });
    expect(within(row).getAllByRole("cell").at(-1)).toHaveTextContent("—");
  });

  it("states the average, the yearly rupees and how much of the portfolio it covers", () => {
    render(<DataPanel data={withFees()} />);
    const line = within(panel()).getByText(/Fund costs/);
    expect(line).toHaveTextContent("0.46% a year");
    expect(line).toHaveTextContent("₹3,350");
    expect(line).toHaveTextContent("70.0% of the portfolio");
  });

  it("names the funds whose ratio is not known", () => {
    render(<DataPanel data={withFees({ expense_unknown: ["BIGFUND", "OTHER"] })} />);
    expect(within(panel()).getByText("Expense ratio not known for: BIGFUND, OTHER")).toBeInTheDocument();
  });

  it("calls the demo ratios illustrative", () => {
    render(<DataPanel data={withFees({}, ["sample"])} />);
    expect(within(panel()).getByText(/illustrative/i)).toBeInTheDocument();
  });

  it("does not call a real broker's ratios illustrative", () => {
    render(<DataPanel data={withFees()} />);
    expect(within(panel()).queryByText(/illustrative/i)).toBeNull();
  });

  it("shows no fee column, no cost line and no unknown line when nothing is known", () => {
    render(<DataPanel data={portfolioData()} />);
    expect(within(panel()).queryByRole("columnheader", { name: "Fee" })).toBeNull();
    expect(within(panel()).queryByText(/Fund costs/)).toBeNull();
    expect(within(panel()).queryByText(/not known/)).toBeNull();
  });

  it("still names unknown funds when no ratio is known at all", () => {
    render(<DataPanel data={portfolioData({ expense_unknown: ["FUND"] })} />);
    expect(within(panel()).getByText("Expense ratio not known for: FUND")).toBeInTheDocument();
    expect(within(panel()).queryByRole("columnheader", { name: "Fee" })).toBeNull();
  });

  it("ignores malformed cost numbers instead of printing NaN", () => {
    render(<DataPanel data={withFees({ weighted_expense_ratio_pct: "x", annual_fund_cost: null, expense_covered_pct: undefined, expense_unknown: "no" })} />);
    expect(within(panel()).queryByText(/Fund costs/)).toBeNull();
    expect(panel().textContent).not.toMatch(/NaN|undefined/);
  });

  it("shows a ratio of zero as 0.00%, not as a dash", () => {
    const d = withFees();
    (d.metrics.holdings[1] as Record<string, unknown>).expense_ratio_pct = 0;
    render(<DataPanel data={d} />);
    expect(within(panel()).getByText("0.00%")).toBeInTheDocument();
  });
});
