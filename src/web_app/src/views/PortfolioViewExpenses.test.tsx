import { render, screen } from "@testing-library/react";
import { assistant, portfolioData } from "../test/factories";
import { PortfolioView } from "./PortfolioView";

const show = (data: unknown) =>
  render(<PortfolioView messages={[assistant({ agent: "portfolio", text: "Your portfolio.", data: data as Record<string, unknown> })]}
                        pending={false} onSend={async () => null} />);

describe("PortfolioView: fund costs tile", () => {
  it("shows the average yearly cost of the funds", () => {
    show(portfolioData({ weighted_expense_ratio_pct: 0.55, annual_fund_cost: 168.25, expense_covered_pct: 85.92, expense_unknown: [] }));
    expect(screen.getByText("Fund costs").nextElementSibling).toHaveTextContent("0.55% a year");
  });

  it("shows no tile when the cost is not known", () => {
    show(portfolioData());
    expect(screen.queryByText("Fund costs", { selector: "dt" })).toBeNull();
  });

  it("shows no tile for a malformed number", () => {
    show(portfolioData({ weighted_expense_ratio_pct: "0.5" }));
    expect(screen.queryByText("Fund costs", { selector: "dt" })).toBeNull();
  });

  it("keeps the other tiles", () => {
    show(portfolioData({ weighted_expense_ratio_pct: 0.55 }));
    expect(screen.getByText("Diversification")).toBeInTheDocument();
    expect(screen.getByText("Holdings", { selector: "dt" })).toBeInTheDocument();
  });
});
