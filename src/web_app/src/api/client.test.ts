import { fakeFetch, makeResponse } from "../test/factories";
import { ApiError, createApi } from "./client";

const BASE = "http://api.test";

describe("chat", () => {
  it("POSTs the message as JSON and returns the parsed reply", async () => {
    const reply = makeResponse({ text: "hello" });
    const { fetch, calls } = fakeFetch({ body: reply });
    const out = await createApi(BASE, fetch).chat({ message: "hi", thread_id: "abcdefgh" });
    expect(out.text).toBe("hello");
    expect(calls[0].url).toBe(`${BASE}/chat`);
    expect(calls[0].init.method).toBe("POST");
    expect((calls[0].init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ message: "hi", thread_id: "abcdefgh" });
  });

  it("leaves out thread_id and agent when they are not given", async () => {
    const { fetch, calls } = fakeFetch({ body: makeResponse() });
    await createApi(BASE, fetch).chat({ message: "hi" });
    expect(JSON.parse(calls[0].init.body as string)).toEqual({ message: "hi" });
  });

  it("sends an agent hint", async () => {
    const { fetch, calls } = fakeFetch({ body: makeResponse() });
    await createApi(BASE, fetch).chat({ message: "hi", agent: "tax_education" });
    expect(JSON.parse(calls[0].init.body as string).agent).toBe("tax_education");
  });

  it("ignores a trailing slash on the base URL", async () => {
    const { fetch, calls } = fakeFetch({ body: makeResponse() });
    await createApi(`${BASE}/`, fetch).chat({ message: "hi" });
    expect(calls[0].url).toBe(`${BASE}/chat`);
  });

  it("turns a 422 into a readable, non-retryable error", async () => {
    const detail = [{ type: "value_error", loc: ["body", "message"], msg: "Value error, message must not be blank" }];
    const { fetch } = fakeFetch({ status: 422, body: { detail } });
    await expect(createApi(BASE, fetch).chat({ message: " " })).rejects.toMatchObject({
      name: "ApiError", message: "message must not be blank", status: 422, retryable: false,
    });
  });

  it("uses the message of a 422 that has no 'Value error' prefix", async () => {
    const detail = [{ msg: "Input should be 'finance_qa' or 'portfolio'" }];
    const { fetch } = fakeFetch({ status: 422, body: { detail } });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toThrow("Input should be 'finance_qa' or 'portfolio'");
  });

  it("uses the server's own message for a 500 and allows a retry", async () => {
    const { fetch } = fakeFetch({ status: 500, body: { error: "Something went wrong on the server. Please try again." } });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toMatchObject({
      message: "Something went wrong on the server. Please try again.", status: 500, retryable: true,
    });
  });

  it("copes with an error body that is not JSON", async () => {
    const { fetch } = fakeFetch({ status: 502, raw: "<html>Bad gateway</html>" });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toMatchObject({
      message: "The server returned an error (502).", retryable: true,
    });
  });

  it("explains a network failure and names the address", async () => {
    const { fetch } = fakeFetch(new TypeError("Failed to fetch"));
    const err = await createApi(BASE, fetch).chat({ message: "x" }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toContain("can't reach the server");
    expect(err.message).toContain(BASE);
    expect(err.retryable).toBe(true);
  });

  it("gives up on a request that takes too long", async () => {
    const slow = ((_: string, init: RequestInit) =>
      new Promise((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
      })) as unknown as typeof fetch;
    const err = await createApi(BASE, slow, 20).chat({ message: "x" }).catch((e) => e);
    expect(err.message).toContain("taking too long");
    expect(err.retryable).toBe(true);
  });

  it("rejects a reply that is not the documented shape", async () => {
    const { fetch } = fakeFetch({ body: { hello: "world" } });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toThrow("unexpected reply");
  });
});

describe("agents", () => {
  it("GETs the list", async () => {
    const list = [{ name: "finance_qa", ready: true }];
    const { fetch, calls } = fakeFetch({ body: list });
    expect(await createApi(BASE, fetch).agents()).toEqual(list);
    expect(calls[0].url).toBe(`${BASE}/agents`);
    expect(calls[0].init.method ?? "GET").toBe("GET");
  });
});

describe("endSession", () => {
  it("DELETEs the session and accepts a 204", async () => {
    const { fetch, calls } = fakeFetch({ status: 204 });
    await createApi(BASE, fetch).endSession("abcdefgh");
    expect(calls[0].url).toBe(`${BASE}/sessions/abcdefgh`);
    expect(calls[0].init.method).toBe("DELETE");
  });

  it("encodes the id", async () => {
    const { fetch, calls } = fakeFetch({ status: 204 });
    await createApi(BASE, fetch).endSession("a b/c");
    expect(calls[0].url).toBe(`${BASE}/sessions/a%20b%2Fc`);
  });

  it("throws when the server refuses", async () => {
    const { fetch } = fakeFetch({ status: 500, body: { error: "boom" } });
    await expect(createApi(BASE, fetch).endSession("abcdefgh")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("which failures can be retried", () => {
  it.each([400, 401, 403, 404])("does not offer a retry for a %i", async (status) => {
    const { fetch } = fakeFetch({ status, body: { error: "nope" } });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toMatchObject({ status, retryable: false });
  });

  it("does not offer a retry for a 404 that is not JSON", async () => {
    const { fetch } = fakeFetch({ status: 404, raw: "Not found" });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toMatchObject({ status: 404, retryable: false });
  });

  it.each([500, 502, 503])("offers a retry for a %i", async (status) => {
    const { fetch } = fakeFetch({ status, body: { error: "down" } });
    await expect(createApi(BASE, fetch).chat({ message: "x" })).rejects.toMatchObject({ status, retryable: true });
  });
});
