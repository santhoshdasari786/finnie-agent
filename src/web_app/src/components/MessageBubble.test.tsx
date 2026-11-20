import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Message } from "../api/types";
import { assistant, user } from "../test/factories";
import { MessageBubble } from "./MessageBubble";

const noop = () => {};

describe("MessageBubble", () => {
  it("shows what the user said", () => {
    render(<MessageBubble message={user("What is a SIP?")} onSend={noop} onRetry={noop} />);
    expect(screen.getByText("What is a SIP?")).toBeInTheDocument();
    expect(screen.getByLabelText("You")).toBeInTheDocument();
  });

  it("shows the user's text as plain text, never as markup", () => {
    const { container } = render(<MessageBubble message={user("<img src=x onerror=alert(1)>")} onSend={noop} onRetry={noop} />);
    expect(container.querySelector("img")).toBeNull();
  });

  it("shows an answer with its agent, text and disclaimer", () => {
    render(<MessageBubble message={assistant({ agent: "tax_education", text: "Gains depend on **holding period**." })} onSend={noop} onRetry={noop} />);
    expect(screen.getByText("Tax")).toBeInTheDocument();
    expect(screen.getByText("holding period").tagName).toBe("STRONG");
    expect(screen.getByText(/not financial advice/i)).toBeInTheDocument();
  });

  it("shows which agents worked together on one answer", () => {
    const a = assistant({ agent: "goal_planning", meta: { collaboration: { agents: ["portfolio", "goal_planning"], starting_balance: 115170 } } });
    render(<MessageBubble message={a} onSend={noop} onRetry={noop} />);
    const note = screen.getByTestId("collaboration");
    expect(note).toHaveTextContent(/worked together/i);
    expect(note.textContent).toMatch(/Portfolio.*Goals/);
  });

  it("shows no collaboration note for an answer from one agent", () => {
    render(<MessageBubble message={assistant({ agent: "goal_planning" })} onSend={noop} onRetry={noop} />);
    expect(screen.queryByTestId("collaboration")).toBeNull();
  });

  it("ignores a collaboration value it does not understand", () => {
    const a = assistant({ meta: { collaboration: { agents: "portfolio" } as never } });
    render(<MessageBubble message={a} onSend={noop} onRetry={noop} />);
    expect(screen.queryByTestId("collaboration")).toBeNull();
  });

  it("shows citations", () => {
    const a = assistant({ citations: [{ source: "https://x.org", title: "Source A", excerpt: "e", verified_at: null }] });
    render(<MessageBubble message={a} onSend={noop} onRetry={noop} />);
    expect(screen.getByRole("link", { name: /Source A/ })).toBeInTheDocument();
  });

  it("shows the structured details", () => {
    const a = assistant({ agent: "portfolio", data: { quotes: [{ instrument: { symbol: "TCS", exchange: "NSE" }, price: 3000, change_pct: 1, currency: "INR", as_of: "2026-11-16T04:00:00Z", source: "yfinance", stale: false }], missing: [] } });
    render(<MessageBubble message={a} onSend={noop} onRetry={noop} />);
    expect(screen.getByRole("row", { name: /TCS/ })).toBeInTheDocument();
  });

  it("offers the login when a login is needed", async () => {
    const onSend = vi.fn();
    const a = assistant({ agent: "portfolio", status: "needs_login", login_url: "https://mcp.kite.trade/authorize", data: { login_url: "https://mcp.kite.trade/authorize" } });
    render(<MessageBubble message={a} onSend={onSend} onRetry={noop} />);
    expect(screen.getByRole("link", { name: /login/i })).toHaveAttribute("href", "https://mcp.kite.trade/authorize");
    await userEvent.click(screen.getByRole("button", { name: /approved/i }));
    expect(onSend).toHaveBeenCalledWith("connect kite");
  });

  it("offers quick replies for a portfolio menu", async () => {
    const onSend = vi.fn();
    const a = assistant({ agent: "portfolio", status: "clarify", data: { options: [{ name: "sample", label: "Sample portfolio" }] } });
    render(<MessageBubble message={a} onSend={onSend} onRetry={noop} />);
    await userEvent.click(screen.getByRole("button", { name: "Sample portfolio" }));
    expect(onSend).toHaveBeenCalledWith("connect sample");
  });

  it("does not show a login prompt for an ordinary answer", () => {
    render(<MessageBubble message={assistant()} onSend={noop} onRetry={noop} />);
    expect(screen.queryByRole("button", { name: /approved/i })).toBeNull();
  });

  it("marks the status for styling", () => {
    render(<MessageBubble message={assistant({ status: "no_source" })} onSend={noop} onRetry={noop} />);
    expect(screen.getByTestId("assistant-message")).toHaveAttribute("data-status", "no_source");
  });

  it("shows an error as an alert with a retry button", async () => {
    const onRetry = vi.fn();
    const m: Message = { id: "e1", role: "error", text: "The server is down.", retryText: "hi" };
    render(<MessageBubble message={m} onSend={noop} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("The server is down.");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("offers no retry for an error that retrying cannot fix", () => {
    const m: Message = { id: "e1", role: "error", text: "message must not be blank", retryText: null };
    render(<MessageBubble message={m} onSend={noop} onRetry={noop} />);
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
  });
});

describe("MessageBubble login rules", () => {
  it("shows no login prompt for an ordinary answer even if a link is present", () => {
    render(<MessageBubble message={assistant({ status: "ok", login_url: "https://mcp.kite.trade/authorize" })} onSend={() => {}} onRetry={() => {}} />);
    expect(screen.queryByRole("button", { name: /approved/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /login/i })).toBeNull();
  });

  it("shows quick replies only for a clarify", () => {
    const a = assistant({ status: "ok", data: { options: [{ name: "sample", label: "Sample portfolio" }] } });
    render(<MessageBubble message={a} onSend={() => {}} onRetry={() => {}} />);
    expect(screen.queryByRole("button", { name: "Sample portfolio" })).toBeNull();
  });
});
