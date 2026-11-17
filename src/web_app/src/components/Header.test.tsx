import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Header } from "./Header";

const agents = [{ name: "finance_qa", ready: true }, { name: "news_synthesizer", ready: false }];

describe("Header", () => {
  it("shows the product name", () => {
    render(<Header agents={[]} onNewChat={() => {}} busy={false} />);
    expect(screen.getByRole("heading", { name: /finnie/i })).toBeInTheDocument();
  });

  it("shows which agents are ready", () => {
    render(<Header agents={agents} onNewChat={() => {}} busy={false} />);
    expect(screen.getByLabelText(/Q&A: ready/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/News: not available/i)).toBeInTheDocument();
  });

  it("starts a new chat", async () => {
    const onNewChat = vi.fn();
    render(<Header agents={[]} onNewChat={onNewChat} busy={false} />);
    await userEvent.click(screen.getByRole("button", { name: /new chat/i }));
    expect(onNewChat).toHaveBeenCalled();
  });

  it("will not start a new chat while an answer is pending", () => {
    render(<Header agents={[]} onNewChat={() => {}} busy />);
    expect(screen.getByRole("button", { name: /new chat/i })).toBeDisabled();
  });

  it("says it is educational, not advice", () => {
    render(<Header agents={[]} onNewChat={() => {}} busy={false} />);
    expect(screen.getByText(/education/i)).toBeInTheDocument();
  });
});
