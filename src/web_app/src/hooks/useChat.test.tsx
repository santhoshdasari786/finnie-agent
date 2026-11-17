import { act, renderHook, waitFor } from "@testing-library/react";
import type { Api } from "../api/client";
import { ApiError } from "../api/client";
import type { ChatRequest } from "../api/types";
import { loadSession } from "../session";
import { makeResponse } from "../test/factories";
import { useChat } from "./useChat";

function fakeApi(over: Partial<Api> = {}): Api & { chats: ChatRequest[]; ended: string[] } {
  const chats: ChatRequest[] = [];
  const ended: string[] = [];
  return {
    chats,
    ended,
    chat: async (req) => {
      chats.push(req);
      return makeResponse({ thread_id: "thread-0001", text: `echo: ${req.message}` });
    },
    agents: async () => [],
    endSession: async (id) => {
      ended.push(id);
    },
    marketHistory: async () => {
      throw new Error("not used here");
    },
    ...over,
  };
}

describe("useChat", () => {
  it("shows the user's message, then the reply", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("What is a SIP?"));
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({ role: "user", text: "What is a SIP?" });
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", response: { text: "echo: What is a SIP?" } });
  });

  it("is pending while the request is in flight", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const api = fakeApi({ chat: async () => { await gate; return makeResponse(); } });
    const { result } = renderHook(() => useChat(api));
    act(() => { void result.current.send("hi"); });
    await waitFor(() => expect(result.current.pending).toBe(true));
    expect(result.current.messages).toHaveLength(1);
    await act(async () => { release(); await gate; });
    await waitFor(() => expect(result.current.pending).toBe(false));
  });

  it("sends no thread id the first time and the returned one afterwards", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("one"));
    await act(() => result.current.send("two"));
    expect(api.chats[0].thread_id).toBeUndefined();
    expect(api.chats[1].thread_id).toBe("thread-0001");
  });

  it("trims the text and ignores blanks", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("   "));
    await act(() => result.current.send("  hello  "));
    expect(api.chats).toEqual([{ message: "hello" }]);
  });

  it("ignores a second send while one is in flight", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const api = fakeApi({ chat: async (req) => { await gate; return makeResponse({ text: req.message }); } });
    const { result } = renderHook(() => useChat(api));
    act(() => { void result.current.send("first"); void result.current.send("second"); });
    await act(async () => { release(); await gate; });
    await waitFor(() => expect(result.current.pending).toBe(false));
    expect(result.current.messages.filter((m) => m.role === "user")).toHaveLength(1);
  });

  it("shows a failure as an error message that remembers what to retry", async () => {
    const api = fakeApi({ chat: async () => { throw new ApiError("The server is down.", 500, true); } });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    expect(result.current.messages[1]).toEqual(expect.objectContaining({ role: "error", text: "The server is down.", retryText: "hi" }));
    expect(result.current.pending).toBe(false);
  });

  it("does not offer a retry for a request the server rejected as invalid", async () => {
    const api = fakeApi({ chat: async () => { throw new ApiError("message must not be blank", 422, false); } });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    expect(result.current.messages[1]).toMatchObject({ role: "error", retryText: null });
  });

  it("describes an unexpected error generically", async () => {
    const api = fakeApi({ chat: async () => { throw new Error("secret stack detail"); } });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    const last = result.current.messages[1];
    expect(last).toMatchObject({ role: "error" });
    expect(JSON.stringify(last)).not.toContain("secret");
  });

  it("retries the failed text and removes the error message", async () => {
    let fail = true;
    const api = fakeApi({
      chat: async (req) => {
        if (fail) { fail = false; throw new ApiError("down", 500, true); }
        return makeResponse({ text: `ok: ${req.message}` });
      },
    });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    await act(() => result.current.retry());
    const roles = result.current.messages.map((m) => m.role);
    expect(roles).toEqual(["user", "assistant"]);
    expect(result.current.messages[1]).toMatchObject({ response: { text: "ok: hi" } });
  });

  it("does not store a thread id after a failure", async () => {
    const api = fakeApi({ chat: async () => { throw new ApiError("down", 500, true); } });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    expect(loadSession().threadId).toBeNull();
  });

  it("saves the conversation and restores it in a new hook", async () => {
    const api = fakeApi();
    const first = renderHook(() => useChat(api));
    await act(() => first.result.current.send("hi"));
    first.unmount();
    const second = renderHook(() => useChat(api));
    expect(second.result.current.messages).toHaveLength(2);
    await act(() => second.result.current.send("again"));
    expect(api.chats[1].thread_id).toBe("thread-0001");
  });

  it("does not save an error message", async () => {
    const api = fakeApi({ chat: async () => { throw new ApiError("down", 500, true); } });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    expect(loadSession().messages.map((m) => m.role)).toEqual(["user"]);
  });

  it("starts a new chat: ends the server session and clears everything", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    await act(() => result.current.newChat());
    expect(api.ended).toEqual(["thread-0001"]);
    expect(result.current.messages).toEqual([]);
    expect(loadSession()).toEqual({ threadId: null, messages: [] });
    await act(() => result.current.send("fresh"));
    expect(api.chats[1].thread_id).toBeUndefined();
  });

  it("starts a new chat even if the server cannot end the old one", async () => {
    const api = fakeApi({ endSession: async () => { throw new ApiError("down", 500, true); } });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    await act(() => result.current.newChat());
    expect(result.current.messages).toEqual([]);
  });

  it("does not call the server to end a chat that never started", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.newChat());
    expect(api.ended).toEqual([]);
  });

  it("gives each message its own id", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("a"));
    await act(() => result.current.send("b"));
    const ids = result.current.messages.map((m) => m.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe("useChat while an answer is pending", () => {
  it("ignores New chat until the answer arrives", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const ended: string[] = [];
    const api = fakeApi({ chat: async () => { await gate; return makeResponse({ thread_id: "thread-0001" }); }, endSession: async (id) => { ended.push(id); } });
    const { result } = renderHook(() => useChat(api));
    act(() => { void result.current.send("hi"); });
    await waitFor(() => expect(result.current.pending).toBe(true));
    await act(() => result.current.newChat());
    expect(result.current.messages).toHaveLength(1);
    expect(ended).toEqual([]);
    await act(async () => { release(); await gate; });
    await waitFor(() => expect(result.current.pending).toBe(false));
    expect(result.current.messages).toHaveLength(2);
  });
});
