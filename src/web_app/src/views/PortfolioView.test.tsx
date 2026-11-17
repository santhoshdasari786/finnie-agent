import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AgentName, ChatResponse, Message } from "../api/types";
import { assistant, makeResponse, portfolioData, user } from "../test/factories";
import { PortfolioView } from "./PortfolioView";

type Send = (text: string, agent?: AgentName) => Promise<ChatResponse | null>;

function setup(messages: Message[] = [], { pending = false, replies = [] as Array<ChatResponse | null> } = {}) {
  const queue = [...replies];
  const onSend = vi.fn<Send>(async () => (queue.length ? queue.shift()! : makeResponse({ agent: "portfolio" })));
  const utils = render(<PortfolioView messages={messages} pending={pending} onSend={onSend} />);
  return { onSend, ...utils };
}

const analysis = (over = {}) => assistant({ agent: "portfolio", text: "Your portfolio is worth about ten lakh.", data: portfolioData(), ...over });
const sentTexts = (onSend: ReturnType<typeof setup>["onSend"]) => onSend.mock.calls.map((c) => c[0]);

describe("PortfolioView: before there is an analysis", () => {
  it("explains what it does and offers the two sources", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Portfolio" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze the sample portfolio" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Connect Zerodha (read-only)" })).toBeEnabled();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("the sample button connects the sample, then analyses it", async () => {
    const { onSend } = setup([], { replies: [makeResponse({ agent: "portfolio", status: "ok" }), makeResponse({ agent: "portfolio", status: "ok" })] });
    await userEvent.click(screen.getByRole("button", { name: "Analyze the sample portfolio" }));
    expect(onSend.mock.calls).toEqual([["connect sample", "portfolio"], ["analyze my portfolio", "portfolio"]]);
  });

  it("does not analyse when connecting failed", async () => {
    const { onSend } = setup([], { replies: [makeResponse({ agent: "portfolio", status: "error" })] });
    await userEvent.click(screen.getByRole("button", { name: "Analyze the sample portfolio" }));
    expect(sentTexts(onSend)).toEqual(["connect sample"]);
  });

  it("does not analyse when the request itself failed", async () => {
    const { onSend } = setup([], { replies: [null] });
    await userEvent.click(screen.getByRole("button", { name: "Analyze the sample portfolio" }));
    expect(sentTexts(onSend)).toEqual(["connect sample"]);
  });

  it("the Zerodha button connects kite, and analyses when it is already connected", async () => {
    const { onSend } = setup([], { replies: [makeResponse({ agent: "portfolio", status: "ok" }), makeResponse({ agent: "portfolio", status: "ok" })] });
    await userEvent.click(screen.getByRole("button", { name: "Connect Zerodha (read-only)" }));
    expect(onSend.mock.calls).toEqual([["connect kite", "portfolio"], ["analyze my portfolio", "portfolio"]]);
  });

  it("the Zerodha button stops at the login step", async () => {
    const { onSend } = setup([], { replies: [makeResponse({ agent: "portfolio", status: "needs_login", login_url: "https://kite.example/login" })] });
    await userEvent.click(screen.getByRole("button", { name: "Connect Zerodha (read-only)" }));
    expect(sentTexts(onSend)).toEqual(["connect kite"]);
  });

  it("both buttons are off while a request is running", () => {
    setup([], { pending: true });
    expect(screen.getByRole("button", { name: "Analyze the sample portfolio" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Connect Zerodha (read-only)" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/working on it/i);
  });

  it("shows no status when nothing is running", () => {
    setup();
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("PortfolioView: the login step", () => {
  const needsLogin = assistant({ agent: "portfolio", status: "needs_login", text: "Open the link.", login_url: "https://kite.example/login" });

  it("shows the login button for a pending login", () => {
    setup([needsLogin]);
    expect(screen.getByRole("link", { name: "Open Zerodha login" })).toHaveAttribute("href", "https://kite.example/login");
  });

  it("'I've approved it' connects, and analyses once connected", async () => {
    const { onSend } = setup([needsLogin], { replies: [makeResponse({ agent: "portfolio", status: "ok" }), makeResponse({ agent: "portfolio", status: "ok" })] });
    await userEvent.click(screen.getByRole("button", { name: "I've approved it" }));
    expect(onSend.mock.calls).toEqual([["connect kite", "portfolio"], ["analyze my portfolio", "portfolio"]]);
  });

  it("'I've approved it' stops when the login is still not done", async () => {
    const { onSend } = setup([needsLogin], { replies: [makeResponse({ agent: "portfolio", status: "needs_login", login_url: "https://kite.example/login" })] });
    await userEvent.click(screen.getByRole("button", { name: "I've approved it" }));
    expect(sentTexts(onSend)).toEqual(["connect kite"]);
  });

  it("shows the login button only for a reply that needs a login", () => {
    setup([assistant({ agent: "portfolio", status: "ok", login_url: "https://kite.example/login" })]);
    expect(screen.queryByRole("link", { name: "Open Zerodha login" })).toBeNull();
  });

  it("hides the login prompt once an analysis is newer", () => {
    setup([needsLogin, analysis()]);
    expect(screen.queryByRole("link", { name: "Open Zerodha login" })).toBeNull();
  });
});

describe("PortfolioView: with an analysis", () => {
  it("shows the asset-class donut and the holdings bars", () => {
    setup([analysis()]);
    expect(screen.getByRole("img", { name: "Allocation by asset class: equity 60.0%, gold 40.0%" })).toBeInTheDocument();
    const bars = screen.getByRole("list", { name: "Holdings by share" });
    expect(within(bars).getAllByRole("listitem").map((r) => r.textContent)).toEqual(["GOLDBEES40.0%", "TCS30.0%", "INFY30.0%"]);
  });

  it("shows the headline numbers", () => {
    setup([analysis()]);
    expect(screen.getByText("0.66 / 1")).toBeInTheDocument();
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    expect(screen.getByText("Largest holding")).toBeInTheDocument();
    expect(screen.getByText("40.0%", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText("Holdings", { selector: "dt" }).nextSibling).toHaveTextContent("3");
  });

  it("shows the holdings table, the total and the demo-data notice", () => {
    setup([analysis()]);
    const details = screen.getByRole("region", { name: "Portfolio details" });
    expect(within(details).getByText("₹1,000,000")).toBeInTheDocument();
    expect(within(details).getByText(/demo data/i)).toBeInTheDocument();
    expect(within(details).getAllByRole("row")).toHaveLength(4);
  });

  it("writes the diversification score to two decimals", () => {
    setup([analysis({ data: portfolioData({ diversification_score: 0.5 }) })]);
    expect(screen.getByText("0.50 / 1")).toBeInTheDocument();
  });

  it("puts the total value in the middle of the donut", () => {
    setup([analysis()]);
    expect(within(screen.getByRole("heading", { name: "Asset classes" }).parentElement!).getByText("₹1M")).toBeInTheDocument();
  });

  it("shows the explanation and the disclaimer", () => {
    setup([analysis({ disclaimer: "Educational only." })]);
    expect(screen.getByText("Your portfolio is worth about ten lakh.")).toBeInTheDocument();
    expect(screen.getByText("Educational only.")).toBeInTheDocument();
  });

  it("uses the newest analysis", () => {
    setup([analysis({ text: "old one" }), user("again"), analysis({ text: "new one" })]);
    expect(screen.getByText("new one")).toBeInTheDocument();
    expect(screen.queryByText("old one")).toBeNull();
  });

  it("'Refresh analysis' asks again", async () => {
    const { onSend } = setup([analysis()]);
    await userEvent.click(screen.getByRole("button", { name: "Refresh analysis" }));
    expect(onSend.mock.calls).toEqual([["analyze my portfolio", "portfolio"]]);
  });

  it("does not offer the first-time buttons any more", () => {
    setup([analysis()]);
    expect(screen.queryByRole("button", { name: "Analyze the sample portfolio" })).toBeNull();
  });

  it("disables refresh while a request is running", () => {
    setup([analysis()], { pending: true });
    expect(screen.getByRole("button", { name: "Refresh analysis" })).toBeDisabled();
  });

  it("names holdings that could not be priced", () => {
    setup([analysis({ data: portfolioData({ unpriced: ["XYZ"] }) })]);
    expect(screen.getByText(/couldn't price: XYZ/i)).toBeInTheDocument();
  });

  it("does not draw a chart for data it cannot read", () => {
    setup([analysis({ data: { metrics: { total_value: "lots" } } })]);
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("ignores analyses and metrics from other agents", () => {
    setup([assistant({ agent: "finance_qa", data: portfolioData() })]);
    expect(screen.getByRole("button", { name: "Analyze the sample portfolio" })).toBeInTheDocument();
  });
});

describe("PortfolioView: when the last answer was a problem", () => {
  it("shows an error from the portfolio agent as an alert", () => {
    setup([assistant({ agent: "portfolio", status: "error", text: "I couldn't price any of your holdings right now." })]);
    expect(screen.getByRole("alert")).toHaveTextContent("I couldn't price any of your holdings right now.");
  });

  it("keeps showing the last good analysis under the alert", () => {
    setup([analysis(), assistant({ agent: "portfolio", status: "error", text: "Could not refresh." })]);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not refresh.");
    expect(screen.getByRole("img", { name: /Allocation by asset class/ })).toBeInTheDocument();
  });

  it("an ordinary newer answer clears the alert", () => {
    setup([assistant({ agent: "portfolio", status: "error", text: "Could not refresh." }), analysis()]);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
