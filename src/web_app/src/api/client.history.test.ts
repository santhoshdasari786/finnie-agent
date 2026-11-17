import { fakeFetch, makeHistory } from "../test/factories";
import { ApiError, createApi } from "./client";

const BASE = "http://api.test";

describe("marketHistory", () => {
  it("GETs the symbol and the range", async () => {
    const { fetch, calls } = fakeFetch({ body: makeHistory() });
    await createApi(BASE, fetch).marketHistory("TCS", "3m");
    expect(calls[0].url).toBe(`${BASE}/market/history?symbol=TCS&range=3m`);
    expect(calls[0].init.method ?? "GET").toBe("GET");
  });

  it("encodes the symbol", async () => {
    const { fetch, calls } = fakeFetch({ body: makeHistory() });
    await createApi(BASE, fetch).marketHistory("M&M", "1y");
    expect(calls[0].url).toBe(`${BASE}/market/history?symbol=M%26M&range=1y`);
  });

  it("returns the parsed history", async () => {
    const { fetch } = fakeFetch({ body: makeHistory({ latest: 123.4 }) });
    expect((await createApi(BASE, fetch).marketHistory("TCS", "3m")).latest).toBe(123.4);
  });

  it("explains a 404 in the server's words, and does not suggest retrying", async () => {
    const { fetch } = fakeFetch({ status: 404, body: { error: "I couldn't find price history for NOSUCH." } });
    const err = await createApi(BASE, fetch).marketHistory("NOSUCH", "3m").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("I couldn't find price history for NOSUCH.");
    expect(err.retryable).toBe(false);
  });

  it("a 422 shows the validation message and is not retryable", async () => {
    const { fetch } = fakeFetch({ status: 422, body: { detail: "Unsupported symbol. Use a stock ticker such as TCS, or one of: Nifty 50, Sensex." } });
    const err = await createApi(BASE, fetch).marketHistory("^GSPC", "3m").catch((e) => e);
    expect(err.message).toMatch(/Nifty 50/);
    expect(err.retryable).toBe(false);
  });

  it("a 502 is retryable", async () => {
    const { fetch } = fakeFetch({ status: 502, body: { error: "I couldn't load price history right now. Please try again." } });
    const err = await createApi(BASE, fetch).marketHistory("TCS", "3m").catch((e) => e);
    expect(err.retryable).toBe(true);
    expect(err.message).toMatch(/try again/);
  });

  it("accepts an unknown change (null)", async () => {
    const { fetch } = fakeFetch({ body: makeHistory({ change_pct: null }) });
    expect((await createApi(BASE, fetch).marketHistory("TCS", "3m")).change_pct).toBeNull();
  });

  it("rejects a reply that is not a price history", async () => {
    const { fetch } = fakeFetch({ body: { symbol: "TCS" } });
    await expect(createApi(BASE, fetch).marketHistory("TCS", "3m")).rejects.toThrow("The server sent an unexpected reply.");
  });

  it.each([
    ["points", { points: "no" }],
    ["a point", { points: [{ date: "2026-08-03" }] }],
    ["latest", { latest: "x" }],
    ["currency", { currency: 5 }],
    ["high", { high: "x" }],
    ["low", { low: null }],
    ["change", { change_pct: "x" }],
    ["source", { source: 1 }],
  ])("rejects a reply with a bad %s", async (_, bad) => {
    const { fetch } = fakeFetch({ body: { ...makeHistory(), ...bad } });
    await expect(createApi(BASE, fetch).marketHistory("TCS", "3m")).rejects.toBeInstanceOf(ApiError);
  });

  it("can't-reach and timeout errors behave like the other calls", async () => {
    const { fetch } = fakeFetch(new TypeError("network"));
    await expect(createApi(BASE, fetch).marketHistory("TCS", "3m")).rejects.toThrow(/can't reach the server/);
  });
});
