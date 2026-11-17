import { assistant, user } from "./test/factories";
import { clearSession, loadSession, saveSession } from "./session";

describe("session storage", () => {
  it("starts empty", () => {
    expect(loadSession()).toEqual({ threadId: null, messages: [] });
  });

  it("round-trips the thread id and the messages", () => {
    const messages = [user("hi"), assistant()];
    saveSession("thread-0001", messages);
    expect(loadSession()).toEqual({ threadId: "thread-0001", messages });
  });

  it("keeps only the newest 60 messages", () => {
    const many = Array.from({ length: 80 }, (_, i) => user(`m${i}`, `id${i}`));
    saveSession("thread-0001", many);
    const { messages } = loadSession();
    expect(messages).toHaveLength(60);
    expect(messages[0]).toMatchObject({ text: "m20" });
    expect(messages[59]).toMatchObject({ text: "m79" });
  });

  it("clears everything", () => {
    saveSession("thread-0001", [user("hi")]);
    clearSession();
    expect(loadSession()).toEqual({ threadId: null, messages: [] });
  });

  it("ignores corrupt stored data", () => {
    sessionStorage.setItem("finnie.messages", "{not json");
    sessionStorage.setItem("finnie.thread", "thread-0001");
    expect(loadSession()).toEqual({ threadId: "thread-0001", messages: [] });
  });

  it("ignores stored data that is not a list of messages", () => {
    sessionStorage.setItem("finnie.messages", JSON.stringify({ a: 1 }));
    expect(loadSession().messages).toEqual([]);
  });

  it("drops stored entries that are not messages", () => {
    sessionStorage.setItem("finnie.messages", JSON.stringify([user("ok"), { role: "hacker" }, 5, null]));
    expect(loadSession().messages).toEqual([user("ok")]);
  });

  it("never throws when storage is unavailable", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    expect(() => saveSession("thread-0001", [user("hi")])).not.toThrow();
    spy.mockRestore();
    const get = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    expect(loadSession()).toEqual({ threadId: null, messages: [] });
    get.mockRestore();
  });

  it("removes the thread when saving null", () => {
    saveSession("thread-0001", [user("hi")]);
    saveSession(null, []);
    expect(sessionStorage.getItem("finnie.thread")).toBeNull();
  });
});

describe("what is written to storage", () => {
  it("never writes an error message", () => {
    saveSession("thread-0001", [user("hi"), { id: "e1", role: "error", text: "down", retryText: "hi" }]);
    const raw = JSON.parse(sessionStorage.getItem("finnie.messages")!);
    expect(raw).toHaveLength(1);
    expect(raw[0].role).toBe("user");
  });

  it("never writes more than 60 messages", () => {
    saveSession("thread-0001", Array.from({ length: 100 }, (_, i) => user(`m${i}`, `id${i}`)));
    expect(JSON.parse(sessionStorage.getItem("finnie.messages")!)).toHaveLength(60);
  });
});
