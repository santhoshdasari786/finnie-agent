import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AgentName, ChatResponse, Message } from "../api/types";
import { assistant, goalData, makeResponse } from "../test/factories";
import { GoalsView } from "./GoalsView";

type Send = (text: string, agent?: AgentName) => Promise<ChatResponse | null>;

function setup(messages: Message[] = [], pending = false) {
  const onSend = vi.fn<Send>(async () => makeResponse({ agent: "goal_planning" }));
  render(<GoalsView messages={messages} pending={pending} onSend={onSend} />);
  return onSend;
}

const field = (name: RegExp | string) => screen.getByLabelText(name);
const plan = (over = {}) => assistant({ agent: "goal_planning", text: "Here is what the numbers say.", data: goalData(), ...over });

async function fill(values: Record<string, string>) {
  for (const [label, value] of Object.entries(values)) {
    await userEvent.clear(field(label));
    if (value) await userEvent.type(field(label), value);
  }
}
const submit = () => userEvent.click(screen.getByRole("button", { name: "Plan my goal" }));

describe("GoalsView: the form", () => {
  it("has a heading and the six fields", () => {
    setup();
    expect(screen.getByRole("heading", { name: "Goal planner" })).toBeInTheDocument();
    for (const label of ["Years to goal", "Target amount (₹)", "Monthly saving (₹)", "Starting balance (₹)", "Risk appetite", "Assumed yearly return (%)"]) {
      expect(field(label)).toBeInTheDocument();
    }
  });

  it("offers the three risk levels and 'Not sure'", () => {
    setup();
    const options = within(field("Risk appetite")).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Not sure", "Conservative", "Moderate", "Aggressive"]);
    expect(field("Risk appetite")).toHaveValue("");
  });

  it("sends the question to the goal agent", async () => {
    const onSend = setup();
    await fill({ "Years to goal": "10", "Target amount (₹)": "50,00,000", "Monthly saving (₹)": "20000" });
    await userEvent.selectOptions(field("Risk appetite"), "aggressive");
    await submit();
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith(
      "New goal: Can I reach 5000000 rupees in 10 years, saving 20000 rupees a month? My risk appetite is aggressive.", "goal_planning");
  });

  it("passes the assumed return on", async () => {
    const onSend = setup();
    await fill({ "Years to goal": "10", "Monthly saving (₹)": "5000", "Assumed yearly return (%)": "12" });
    await submit();
    expect(onSend.mock.calls[0][0]).toBe("New goal: What will I have in 10 years, saving 5000 rupees a month? Assume 12% returns.");
  });

  it("asks how long it will take when there are no years", async () => {
    const onSend = setup();
    await fill({ "Target amount (₹)": "5000000", "Monthly saving (₹)": "20000" });
    await submit();
    expect(onSend.mock.calls[0][0]).toBe("New goal: How long will it take to reach 5000000 rupees, saving 20000 rupees a month?");
  });

  it("shows what is wrong, and sends nothing", async () => {
    const onSend = setup();
    await submit();
    expect(screen.getByRole("alert")).toHaveTextContent(/years/i);
    expect(onSend).not.toHaveBeenCalled();
  });

  it("lists every problem it found", async () => {
    setup();
    await fill({ "Years to goal": "99", "Monthly saving (₹)": "lots", "Assumed yearly return (%)": "50" });
    await submit();
    const text = screen.getByRole("alert").textContent ?? "";
    expect(text).toMatch(/Years must be more than 0 and at most 60/);
    expect(text).toMatch(/Monthly saving must be a number/);
    expect(text).toMatch(/Yearly return must be between 0 and 30/);
  });

  it("marks the fields that are wrong", async () => {
    setup();
    await fill({ "Years to goal": "99", "Monthly saving (₹)": "1000" });
    await submit();
    expect(field("Years to goal")).toHaveAttribute("aria-invalid", "true");
    expect(field("Monthly saving (₹)")).not.toHaveAttribute("aria-invalid", "true");
  });

  it("the problems go away once the form is right", async () => {
    setup();
    await submit();
    await fill({ "Years to goal": "10", "Monthly saving (₹)": "1000" });
    await submit();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps what was typed after sending", async () => {
    setup();
    await fill({ "Years to goal": "10", "Monthly saving (₹)": "1000" });
    await submit();
    expect(field("Years to goal")).toHaveValue("10");
  });

  it("'Clear' empties the form and the problems", async () => {
    setup();
    await fill({ "Years to goal": "99" });
    await submit();
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(field("Years to goal")).toHaveValue("");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("can't be submitted twice while a request is running", async () => {
    setup([], true);
    expect(screen.getByRole("button", { name: "Plan my goal" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/working on it/i);
  });

  it("explains that amounts are in rupees and may use commas", () => {
    setup();
    expect(screen.getByText(/rupees/i)).toBeInTheDocument();
  });
});

describe("GoalsView: the result", () => {
  it("shows nothing before a plan", () => {
    setup();
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("region", { name: "Plan details" })).toBeNull();
  });

  it("draws the projected balance with one line per scenario", () => {
    setup([plan()]);
    expect(screen.getByRole("img", { name: /projected balance/i })).toBeInTheDocument();
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(within(legend).getAllByRole("listitem").map((i) => i.textContent)).toEqual(["Pessimistic 3%", "Expected 7%", "Optimistic 11%"]);
  });

  it("marks the target on the chart", () => {
    setup([plan()]);
    expect(screen.getByTestId("ref-line")).toBeInTheDocument();
    expect(screen.getByText("Target ₹5,000,000")).toBeInTheDocument();
  });

  it("has no target line when the goal has no target", () => {
    const data = goalData();
    (data.plan as { target: number | null }).target = null;
    setup([plan({ data })]);
    expect(screen.queryByTestId("ref-line")).toBeNull();
  });

  it("labels the x axis in years", () => {
    setup([plan()]);
    const axis = screen.getByTestId("x-axis");
    expect(within(axis).getByText("Year 0")).toBeInTheDocument();
    expect(within(axis).getByText("Year 10")).toBeInTheDocument();
  });

  it("shows the table under the chart, and the explanation and disclaimer", () => {
    setup([plan({ disclaimer: "Illustrative, not advice." })]);
    expect(screen.getByRole("region", { name: "Plan details" })).toBeInTheDocument();
    expect(screen.getByText("Here is what the numbers say.")).toBeInTheDocument();
    expect(screen.getByText("Illustrative, not advice.")).toBeInTheDocument();
  });

  it("without paths (a 'how long' answer) it shows the table but no chart", () => {
    const data = goalData();
    delete (data as { paths?: unknown }).paths;
    setup([plan({ data })]);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByRole("region", { name: "Plan details" })).toBeInTheDocument();
  });

  it("shows the newest plan", () => {
    setup([plan({ text: "first plan" }), plan({ text: "second plan" })]);
    expect(screen.getByText("second plan")).toBeInTheDocument();
    expect(screen.queryByText("first plan")).toBeNull();
  });

  it("shows a question from the goal agent so the user can answer it", () => {
    setup([assistant({ agent: "goal_planning", status: "clarify", text: "How many years do you have for this goal?" })]);
    expect(screen.getByText("How many years do you have for this goal?")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("an error from the goal agent is an alert", () => {
    setup([assistant({ agent: "goal_planning", status: "error", text: "Something went wrong." })]);
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.");
    expect(screen.getAllByText("Something went wrong.")).toHaveLength(1);          // the alert only, not a second card
  });

  it("ignores other agents' answers", () => {
    setup([assistant({ agent: "finance_qa", text: "about SIPs" })]);
    expect(screen.queryByText("about SIPs")).toBeNull();
  });
});
