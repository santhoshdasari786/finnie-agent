import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { ApiError, type Api } from "./api/client";
import type { ChatRequest } from "./api/types";
import { saveSession } from "./session";
import { assistant, makeResponse, user } from "./test/factories";

function fakeApi(over: Partial<Api> = {}): Api & { chats: ChatRequest[]; ended: string[] } {
  const chats: ChatRequest[] = [];
  const ended: string[] = [];
  return {
    chats, ended,
    chat: async (req) => {
      chats.push(req);
      return makeResponse({ thread_id: "thread-0001", text: `answer to: ${req.message}` });
    },
    agents: async () => [{ name: "finance_qa", ready: true }, { name: "news_synthesizer", ready: false }],
    endSession: async (id) => { ended.push(id); },
    marketHistory: async () => { throw new Error("not used here"); },
    ...over,
  };
}

describe("App", () => {
  it("starts with a welcome and some suggestions", () => {
    render(<App api={fakeApi()} />);
    expect(screen.getByRole("heading", { name: /finnie/i })).toBeInTheDocument();
    expect(screen.getByText(/what would you like to know/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /sip|tax|retire|news|portfolio|reach/i }).length).toBeGreaterThan(0);
  });

  it("answers a typed question and hides the suggestions", async () => {
    render(<App api={fakeApi()} />);
    await userEvent.type(screen.getByRole("textbox"), "What is a SIP?{Enter}");
    expect(await screen.findByText("answer to: What is a SIP?")).toBeInTheDocument();
    expect(screen.getByText("What is a SIP?")).toBeInTheDocument();
    expect(screen.queryByText(/what would you like to know/i)).toBeNull();
  });

  it("sends a clicked suggestion", async () => {
    const api = fakeApi();
    render(<App api={api} />);
    await userEvent.click(screen.getAllByRole("button", { name: /sip/i })[0]);
    await waitFor(() => expect(api.chats).toHaveLength(1));
    expect(api.chats[0].message).toMatch(/sip/i);
  });

  it("shows that it is thinking, and blocks the box meanwhile", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const api = fakeApi({ chat: async () => { await gate; return makeResponse({ text: "done" }); } });
    render(<App api={api} />);
    await userEvent.type(screen.getByRole("textbox"), "hi{Enter}");
    expect(await screen.findByRole("status")).toHaveTextContent(/thinking/i);
    expect(screen.getByRole("textbox")).toBeDisabled();
    release();
    expect(await screen.findByText("done")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.getByRole("textbox")).toBeEnabled();
  });

  it("shows a failure and retries it", async () => {
    let fail = true;
    const api = fakeApi({
      chat: async (req) => {
        if (fail) { fail = false; throw new ApiError("I can't reach the server.", undefined, true); }
        return makeResponse({ text: `ok: ${req.message}` });
      },
    });
    render(<App api={api} />);
    await userEvent.type(screen.getByRole("textbox"), "hello{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("can't reach the server");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("ok: hello")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("sends the connect command when a portfolio source is picked", async () => {
    const api = fakeApi({
      chat: async (req) => req.message === "connect sample"
        ? makeResponse({ agent: "portfolio", text: "Connected." })
        : makeResponse({ agent: "portfolio", status: "clarify", text: "Pick one:", data: { options: [{ name: "sample", label: "Sample portfolio" }] } }),
    });
    const spy = vi.spyOn(api, "chat");
    render(<App api={api} />);
    await userEvent.type(screen.getByRole("textbox"), "connect to my portfolio{Enter}");
    await userEvent.click(await screen.findByRole("button", { name: "Sample portfolio" }));
    expect(await screen.findByText("Connected.")).toBeInTheDocument();
    expect(spy.mock.calls.map((c) => c[0].message)).toEqual(["connect to my portfolio", "connect sample"]);
  });

  it("handles the Kite login round trip", async () => {
    const api = fakeApi({
      chat: async (req) => req.message === "connect kite" && api_state.approved
        ? makeResponse({ agent: "portfolio", text: "Connected to Zerodha Kite." })
        : makeResponse({ agent: "portfolio", status: "needs_login", text: "Open the link.", login_url: "https://mcp.kite.trade/authorize", data: { login_url: "https://mcp.kite.trade/authorize" } }),
    });
    const api_state = { approved: false };
    render(<App api={api} />);
    await userEvent.type(screen.getByRole("textbox"), "connect kite{Enter}");
    expect(await screen.findByRole("link", { name: /login/i })).toHaveAttribute("href", "https://mcp.kite.trade/authorize");
    api_state.approved = true;
    await userEvent.click(screen.getByRole("button", { name: /approved/i }));
    expect(await screen.findByText("Connected to Zerodha Kite.")).toBeInTheDocument();
  });

  it("starts a new chat: ends the session and shows the welcome again", async () => {
    const api = fakeApi();
    render(<App api={api} />);
    await userEvent.type(screen.getByRole("textbox"), "hi{Enter}");
    await screen.findByText("answer to: hi");
    await userEvent.click(screen.getByRole("button", { name: /new chat/i }));
    await waitFor(() => expect(api.ended).toEqual(["thread-0001"]));
    expect(screen.getByText(/what would you like to know/i)).toBeInTheDocument();
    expect(screen.queryByText("answer to: hi")).toBeNull();
  });

  it("restores the conversation after a reload", () => {
    saveSession("thread-0001", [user("earlier question"), assistant({ text: "earlier answer" })]);
    render(<App api={fakeApi()} />);
    expect(screen.getByText("earlier question")).toBeInTheDocument();
    expect(screen.getByText("earlier answer")).toBeInTheDocument();
    expect(screen.queryByText(/what would you like to know/i)).toBeNull();
  });

  it("shows which agents are ready", async () => {
    render(<App api={fakeApi()} />);
    expect(await screen.findByLabelText(/Q&A: ready/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/News: not available/i)).toBeInTheDocument();
  });

  it("still works when the agent list cannot be loaded", async () => {
    const api = fakeApi({ agents: async () => { throw new ApiError("down"); } });
    render(<App api={api} />);
    await userEvent.type(screen.getByRole("textbox"), "hi{Enter}");
    expect(await screen.findByText("answer to: hi")).toBeInTheDocument();
  });

  it("announces new messages to screen readers", () => {
    render(<App api={fakeApi()} />);
    expect(screen.getByRole("log")).toHaveAttribute("aria-live", "polite");
  });
});
