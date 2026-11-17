import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPrompt } from "./LoginPrompt";

describe("LoginPrompt", () => {
  it("offers the login link in a new tab", () => {
    render(<LoginPrompt url="https://mcp.kite.trade/authorize?x=1" onSend={() => {}} />);
    const link = screen.getByRole("link", { name: /open.*login/i });
    expect(link).toHaveAttribute("href", "https://mcp.kite.trade/authorize?x=1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("lets the user say they approved, which asks to connect again", async () => {
    const onSend = vi.fn();
    render(<LoginPrompt url="https://mcp.kite.trade/authorize" onSend={onSend} />);
    await userEvent.click(screen.getByRole("button", { name: /approved/i }));
    expect(onSend).toHaveBeenCalledWith("connect kite");
  });

  it("accepts a local http link for development", () => {
    render(<LoginPrompt url="http://localhost:3000/login" onSend={() => {}} />);
    expect(screen.getByRole("link")).toBeInTheDocument();
  });

  it.each(["javascript:alert(1)", "data:text/html,x", "not a url", ""])("refuses %s", (url) => {
    render(<LoginPrompt url={url} onSend={() => {}} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText(/couldn't be shown safely/i)).toBeInTheDocument();
  });
});
