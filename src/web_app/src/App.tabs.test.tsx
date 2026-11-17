import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { Api } from "./api/client";
import type { ChatRequest, ChatResponse } from "./api/types";
import { goalData, makeHistory, makeResponse, portfolioData } from "./test/factories";

function fakeApi(over: Partial<Api> = {}) {
  const chats: ChatRequest[] = [];
  const history = vi.fn(async (symbol: string, range: string) => makeHistory({ symbol, name: symbol === "NIFTY50" ? "Nifty 50" : symbol, range: range as never }));
  const api: Api & { chats: ChatRequest[]; history: typeof history } = {
    chats, history,
    chat: async (req): Promise<ChatResponse> => {
      chats.push(req);
      if (req.message === "connect sample") return makeResponse({ agent: "portfolio", text: "Connected to Sample portfolio (demo data).", thread_id: "thread-0001" });
      if (req.message === "analyze my portfolio") return makeResponse({ agent: "portfolio", text: "You hold three things.", data: portfolioData(), thread_id: "thread-0001" });
      if (req.agent === "goal_planning") return makeResponse({ agent: "goal_planning", text: "Goal answer.", data: goalData(), thread_id: "thread-0001" });
      return makeResponse({ thread_id: "thread-0001", text: `answer to: ${req.message}` });
    },
    agents: async () => [],
    endSession: async () => {},
    marketHistory: history as unknown as Api["marketHistory"],
    ...over,
  };
  return api;
}

const tab = (name: string) => screen.getByRole("tab", { name });

describe("App: the sections", () => {
  it("has four tabs and starts on Chat", () => {
    render(<App api={fakeApi()} />);
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Chat", "Portfolio", "Market", "Goals"]);
    expect(tab("Chat")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("textbox")).toBeVisible();
  });

  it("shows one panel at a time, named by its tab", async () => {
    render(<App api={fakeApi()} />);
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Chat");
    await userEvent.click(tab("Portfolio"));
    expect(screen.getByRole("tabpanel")).toHaveAccessibleName("Portfolio");
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("hides a tab you have left", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.click(tab("Portfolio"));
    await userEvent.click(tab("Market"));
    const panels = screen.getAllByRole("tabpanel");
    expect(panels).toHaveLength(1);
    expect(panels[0]).toHaveAccessibleName("Market");
  });

  it("the chat box belongs to the Chat tab only", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.click(tab("Goals"));
    expect(screen.queryByRole("textbox", { name: /message|ask|question/i })).toBeNull();
  });

  it("does not load market prices until the Market tab is opened", async () => {
    const api = fakeApi();
    render(<App api={api} />);
    await new Promise((r) => setTimeout(r, 20));
    expect(api.history).not.toHaveBeenCalled();
    await userEvent.click(tab("Market"));
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(api.history).toHaveBeenCalledTimes(1);
  });

  it("keeps a tab as you left it, without loading it again", async () => {
    const api = fakeApi();
    render(<App api={api} />);
    await userEvent.click(tab("Market"));
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    await screen.findByRole("heading", { name: "TCS" });
    await userEvent.click(tab("Chat"));
    await userEvent.click(tab("Market"));
    expect(screen.getByRole("heading", { name: "TCS" })).toBeInTheDocument();
    expect(api.history).toHaveBeenCalledTimes(2);
  });

  it("keeps what you typed in the goal form", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.click(tab("Goals"));
    await userEvent.type(screen.getByLabelText("Years to goal"), "12");
    await userEvent.click(tab("Chat"));
    await userEvent.click(tab("Goals"));
    expect(screen.getByLabelText("Years to goal")).toHaveValue("12");
  });

  it("arrow keys move between tabs", async () => {
    render(<App api={fakeApi()} />);
    tab("Chat").focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(tab("Portfolio")).toHaveAttribute("aria-selected", "true");
    expect(tab("Portfolio")).toHaveFocus();
  });

  it("is still the same header with agent status and a New chat button", () => {
    render(<App api={fakeApi()} />);
    expect(screen.getByRole("heading", { name: /finnie/i, level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New chat" })).toBeInTheDocument();
  });
});

describe("App: the Portfolio tab drives the same conversation", () => {
  it("analyses the sample portfolio and draws it", async () => {
    const api = fakeApi();
    render(<App api={api} />);
    await userEvent.click(tab("Portfolio"));
    await userEvent.click(screen.getByRole("button", { name: "Analyze the sample portfolio" }));
    expect(await screen.findByRole("img", { name: /Allocation by asset class/ })).toBeInTheDocument();
    expect(api.chats.map((c) => [c.message, c.agent])).toEqual([["connect sample", "portfolio"], ["analyze my portfolio", "portfolio"]]);
    expect(api.chats[1].thread_id).toBe("thread-0001");               // the second call reuses the conversation
  });

  it("the same exchange is visible in the Chat tab", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.click(tab("Portfolio"));
    await userEvent.click(screen.getByRole("button", { name: "Analyze the sample portfolio" }));
    await screen.findByRole("img", { name: /Allocation by asset class/ });
    await userEvent.click(tab("Chat"));
    const log = within(screen.getByRole("log"));
    expect(log.getByText("analyze my portfolio")).toBeInTheDocument();
    expect(log.getByText("You hold three things.")).toBeInTheDocument();
  });

  it("an analysis asked for in the chat shows up in the Portfolio tab", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.type(screen.getByRole("textbox"), "analyze my portfolio{Enter}");
    await within(screen.getByRole("log")).findByText("You hold three things.");
    await userEvent.click(tab("Portfolio"));
    expect(screen.getByRole("img", { name: /Allocation by asset class/ })).toBeInTheDocument();
  });

  it("'New chat' clears the portfolio view too", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.click(tab("Portfolio"));
    await userEvent.click(screen.getByRole("button", { name: "Analyze the sample portfolio" }));
    await screen.findByRole("img", { name: /Allocation by asset class/ });
    await userEvent.click(screen.getByRole("button", { name: "New chat" }));
    await waitFor(() => expect(screen.queryByRole("img", { name: /Allocation by asset class/ })).toBeNull());
    expect(screen.getByRole("button", { name: "Analyze the sample portfolio" })).toBeInTheDocument();
  });
});

describe("App: the Goals tab", () => {
  it("sends the form to the goal agent and draws the plan", async () => {
    const api = fakeApi();
    render(<App api={api} />);
    await userEvent.click(tab("Goals"));
    await userEvent.type(screen.getByLabelText("Years to goal"), "10");
    await userEvent.type(screen.getByLabelText("Monthly saving (₹)"), "20000");
    await userEvent.click(screen.getByRole("button", { name: "Plan my goal" }));
    expect(await screen.findByRole("img", { name: /projected balance/i })).toBeInTheDocument();
    expect(api.chats).toHaveLength(1);
    expect(api.chats[0]).toMatchObject({ agent: "goal_planning", message: "New goal: What will I have in 10 years, saving 20000 rupees a month?" });
  });

  it("the question and the answer are in the transcript", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.click(tab("Goals"));
    await userEvent.type(screen.getByLabelText("Years to goal"), "10");
    await userEvent.type(screen.getByLabelText("Monthly saving (₹)"), "20000");
    await userEvent.click(screen.getByRole("button", { name: "Plan my goal" }));
    await screen.findByRole("img", { name: /projected balance/i });
    await userEvent.click(tab("Chat"));
    const log = screen.getByRole("log");
    expect(within(log).getByText("New goal: What will I have in 10 years, saving 20000 rupees a month?")).toBeInTheDocument();
    expect(within(log).getByText("Goal answer.")).toBeInTheDocument();
  });
});
