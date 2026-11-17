import { render, screen } from "@testing-library/react";
import { AgentBadge } from "./AgentBadge";

describe("AgentBadge", () => {
  it.each([
    ["finance_qa", "Q&A"], ["tax_education", "Tax"], ["portfolio", "Portfolio"], ["market_analysis", "Market"],
    ["goal_planning", "Goals"], ["news_synthesizer", "News"], ["guard", "Safety"], ["router", "Assistant"],
  ])("labels %s as %s", (agent, label) => {
    render(<AgentBadge agent={agent} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows an unknown agent by its own name", () => {
    render(<AgentBadge agent="brand_new" />);
    expect(screen.getByText("brand_new")).toBeInTheDocument();
  });

  it("exposes the agent for styling and tests", () => {
    render(<AgentBadge agent="portfolio" />);
    expect(screen.getByText("Portfolio")).toHaveAttribute("data-agent", "portfolio");
  });
});
