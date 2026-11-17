import { act, renderHook } from "@testing-library/react";
import type { Api } from "../api/client";
import { ApiError } from "../api/client";
import type { ChatRequest } from "../api/types";
import { makeResponse } from "../test/factories";
import { useChat } from "./useChat";

function fakeApi(over: Partial<Api> = {}): Api & { chats: ChatRequest[] } {
  const chats: ChatRequest[] = [];
  return {
    chats,
    chat: async (req) => {
      chats.push(req);
      return makeResponse({ thread_id: "thread-0001", text: `echo: ${req.message}` });
    },
    agents: async () => [],
    endSession: async () => {},
    marketHistory: async () => {
      throw new Error("not used here");
    },
    ...over,
  };
}

describe("useChat: sending to a chosen agent", () => {
  it("passes the agent hint to the API", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("connect sample", "portfolio"));
    expect(api.chats[0]).toMatchObject({ message: "connect sample", agent: "portfolio" });
  });

  it("sends no agent key when none is given", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("hi"));
    expect("agent" in api.chats[0]).toBe(false);
  });

  it("returns the reply so the caller can decide what to do next", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    let reply: unknown;
    await act(async () => {
      reply = await result.current.send("hi");
    });
    expect(reply).toMatchObject({ text: "echo: hi", status: "ok" });
  });

  it("returns null when the request failed", async () => {
    const api = fakeApi({ chat: async () => { throw new ApiError("down", 500, true); } });
    const { result } = renderHook(() => useChat(api));
    let reply: unknown = "unset";
    await act(async () => {
      reply = await result.current.send("hi");
    });
    expect(reply).toBeNull();
  });

  it("returns null for a blank message and does not call the server", async () => {
    const api = fakeApi();
    const { result } = renderHook(() => useChat(api));
    let reply: unknown = "unset";
    await act(async () => {
      reply = await result.current.send("   ");
    });
    expect(reply).toBeNull();
    expect(api.chats).toHaveLength(0);
  });

  it("returns null when another request is still running", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    const api = fakeApi({ chat: async () => { await gate; return makeResponse(); } });
    const { result } = renderHook(() => useChat(api));
    let first!: Promise<unknown>;
    act(() => {
      first = result.current.send("one");
    });
    let second: unknown = "unset";
    await act(async () => {
      second = await result.current.send("two");
    });
    expect(second).toBeNull();
    release();
    await act(async () => {
      await first;
    });
  });

  it("a retry keeps the agent the failed message was sent to", async () => {
    let fail = true;
    const api = fakeApi({
      chat: async (req) => {
        api.chats.push(req);
        if (fail) throw new ApiError("down", 500, true);
        return makeResponse({ thread_id: "thread-0001" });
      },
    });
    const { result } = renderHook(() => useChat(api));
    await act(() => result.current.send("connect sample", "portfolio"));
    fail = false;
    await act(() => result.current.retry());
    expect(api.chats).toHaveLength(2);
    expect(api.chats[1]).toMatchObject({ message: "connect sample", agent: "portfolio" });
  });
});
