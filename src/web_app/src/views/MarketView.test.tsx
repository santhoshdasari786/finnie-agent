import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, type Api } from "../api/client";
import type { HistoryRange, MarketHistory } from "../api/types";
import { makeHistory } from "../test/factories";
import { MarketView } from "./MarketView";

type Fetcher = (symbol: string, range: HistoryRange) => Promise<MarketHistory>;

function setup(impl: Fetcher = async (symbol, range) => makeHistory({ symbol, name: symbol === "NIFTY50" ? "Nifty 50" : symbol, range })) {
  const marketHistory = vi.fn<Fetcher>(impl);
  const api = { marketHistory } as unknown as Api;
  render(<MarketView api={api} />);
  return marketHistory;
}

const calls = (fn: ReturnType<typeof setup>) => fn.mock.calls.map((c) => `${c[0]}/${c[1]}`);

describe("MarketView: loading", () => {
  it("starts with the Nifty 50 over three months", async () => {
    const fn = setup();
    expect(await screen.findByRole("heading", { name: "Nifty 50" })).toBeInTheDocument();
    expect(calls(fn)).toEqual(["NIFTY50/3m"]);
  });

  it("says it is loading, then stops", async () => {
    let release!: (h: MarketHistory) => void;
    setup(() => new Promise((r) => (release = r)));
    expect(screen.getByRole("status")).toHaveTextContent("Loading prices…");
    release(makeHistory({ name: "Nifty 50" }));
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("MarketView: the numbers", () => {
  it("shows the latest price and the change over the range", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(screen.getByTestId("latest")).toHaveTextContent("₹110.00");
    const change = screen.getByText("+10.00%");
    expect(change).toHaveAttribute("data-sign", "up");
    expect(screen.getByText("over 3 months")).toBeInTheDocument();
  });

  it("draws a rising line green and a falling one red", async () => {
    setup(async () => makeHistory({ name: "Nifty 50", change_pct: 3 }));
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(document.querySelector("[data-series]")!.getAttribute("class")).toMatch(/emerald/);
  });

  it("a falling line is red", async () => {
    setup(async () => makeHistory({ name: "Nifty 50", change_pct: -3 }));
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(document.querySelector("[data-series]")!.getAttribute("class")).toMatch(/red/);
  });

  it("labels the ends of the chart with the first and last date", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    const axis = screen.getByTestId("x-axis");
    expect(axis).toHaveTextContent("3 Aug 2026");
    expect(axis).toHaveTextContent("6 Aug 2026");
  });

  it("describes the range of the data on screen, not of the button last pressed", async () => {
    // the server answers with a 1-year history whatever the page asked for
    setup(async (symbol) => makeHistory({ symbol, name: "Nifty 50", range: "1y" }));
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(screen.getByText("over 1 year")).toBeInTheDocument();
    expect(screen.queryByText("over 3 months")).toBeNull();
    expect(screen.getByRole("img", { name: /last 1 year/ })).toBeInTheDocument();
  });

  it("shows a range name it does not know as it is", async () => {
    setup(async (symbol) => makeHistory({ symbol, name: "Nifty 50", range: "5y" as never }));
    expect(await screen.findByText("over 5y")).toBeInTheDocument();
  });

  it("while the next range loads, the old numbers are gone rather than mislabelled", async () => {
    let release!: (h: MarketHistory) => void;
    setup((symbol, range) => (range === "3m" ? Promise.resolve(makeHistory({ symbol, name: "Nifty 50", range })) : new Promise((r) => (release = r))));
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: "6M" }));
    expect(screen.queryByText(/over (3|6) months/)).toBeNull();
    release(makeHistory({ name: "Nifty 50", range: "6m" }));
    expect(await screen.findByText("over 6 months")).toBeInTheDocument();
  });

  it("shows a fall in red", async () => {
    setup(async () => makeHistory({ name: "Nifty 50", change_pct: -4.5 }));
    expect(await screen.findByText("-4.50%")).toHaveAttribute("data-sign", "down");
  });

  it("shows a dash when the change is unknown", async () => {
    setup(async () => makeHistory({ name: "Nifty 50", change_pct: null }));
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(screen.getByTestId("change")).toHaveTextContent("—");
  });

  it("shows the high, the low, the source and the date", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(screen.getByText("High").nextSibling).toHaveTextContent("₹110.00");
    expect(screen.getByText("Low").nextSibling).toHaveTextContent("₹100.00");
    expect(screen.getByText(/Source: yfinance · 17 Nov 2026/)).toBeInTheDocument();
  });

  it("draws the closing prices as a chart you can read without seeing it", async () => {
    setup();
    const chart = await screen.findByRole("img", { name: /Nifty 50 closing price/i });
    expect(chart).toHaveAccessibleName(/₹100\.00/);
    expect(chart).toHaveAccessibleName(/₹110\.00/);
    expect(chart).toHaveAccessibleName(/3 Aug 2026/);
    expect(chart).toHaveAccessibleName(/6 Aug 2026/);
  });

  it("says prices may be delayed and are not advice", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(screen.getByText(/can be delayed/i)).toBeInTheDocument();
    expect(screen.getByText(/not financial advice/i)).toBeInTheDocument();
  });

  it("formats prices in the currency it was given", async () => {
    setup(async () => makeHistory({ name: "Apple", currency: "USD", latest: 190, high: 195, low: 180 }));
    await screen.findByRole("heading", { name: "Apple" });
    expect(screen.getByTestId("latest")).toHaveTextContent("$190.00");
  });
});

describe("MarketView: choosing what to see", () => {
  it("offers presets, with the current one pressed", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    for (const label of ["Nifty 50", "Sensex", "RELIANCE", "TCS", "INFY", "HDFCBANK"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.getByRole("button", { name: "Nifty 50" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "TCS" })).toHaveAttribute("aria-pressed", "false");
  });

  it("a preset loads that symbol, keeping the range", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: "6M" }));
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    await screen.findByRole("heading", { name: "TCS" });
    expect(calls(fn)).toEqual(["NIFTY50/3m", "NIFTY50/6m", "TCS/6m"]);
    expect(screen.getByRole("button", { name: "TCS" })).toHaveAttribute("aria-pressed", "true");
  });

  it("offers four ranges, with the current one pressed", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    expect(["1M", "3M", "6M", "1Y"].map((r) => screen.getByRole("button", { name: r }).getAttribute("aria-pressed"))).toEqual(["false", "true", "false", "false"]);
  });

  it.each([["1M", "1m", "1 month"], ["6M", "6m", "6 months"], ["1Y", "1y", "1 year"]])("%s loads %s", async (button, range, words) => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: button }));
    await waitFor(() => expect(calls(fn)).toContain(`NIFTY50/${range}`));
    expect(await screen.findByText(`over ${words}`)).toBeInTheDocument();
  });

  it("clicking what is already chosen does not reload", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: "3M" }));
    await userEvent.click(screen.getByRole("button", { name: "Nifty 50" }));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("a typed symbol is upper-cased and loaded", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.type(screen.getByLabelText("Symbol"), "  wipro ");
    await userEvent.click(screen.getByRole("button", { name: "Show" }));
    await screen.findByRole("heading", { name: "WIPRO" });
    expect(calls(fn)).toEqual(["NIFTY50/3m", "WIPRO/3m"]);
  });

  it("pressing Enter in the box also loads it", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.type(screen.getByLabelText("Symbol"), "ITC{Enter}");
    await screen.findByRole("heading", { name: "ITC" });
    expect(calls(fn)).toContain("ITC/3m");
  });

  it("'nifty' means the Nifty 50 preset", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    await screen.findByRole("heading", { name: "TCS" });
    await userEvent.type(screen.getByLabelText("Symbol"), "nifty{Enter}");
    await waitFor(() => expect(calls(fn)).toEqual(["NIFTY50/3m", "TCS/3m", "NIFTY50/3m"]));
    expect(screen.getByRole("button", { name: "Nifty 50" })).toHaveAttribute("aria-pressed", "true");
  });

  it("accepts index names", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.type(screen.getByLabelText("Symbol"), "sensex{Enter}");
    await waitFor(() => expect(calls(fn)).toContain("SENSEX/3m"));
  });

  it.each(["TCS.NS", "^GSPC", "a b", "<x>", "A".repeat(21)])("refuses %j before asking the server", async (text) => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.type(screen.getByLabelText("Symbol"), `${text}{Enter}`);
    expect(screen.getByRole("alert")).toHaveTextContent("Use a ticker such as TCS, or Nifty or Sensex.");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("an empty box does nothing", async () => {
    const fn = setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: "Show" }));
    expect(fn).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("clears the box after a symbol is loaded", async () => {
    setup();
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.type(screen.getByLabelText("Symbol"), "ITC{Enter}");
    await screen.findByRole("heading", { name: "ITC" });
    expect(screen.getByLabelText("Symbol")).toHaveValue("");
  });
});

describe("MarketView: when something goes wrong", () => {
  it("shows the server's message", async () => {
    setup(async () => { throw new ApiError("I couldn't find price history for NOSUCH.", 404, false); });
    expect(await screen.findByRole("alert")).toHaveTextContent("I couldn't find price history for NOSUCH.");
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("offers 'Try again' when trying again can help", async () => {
    let fail = true;
    const fn = setup(async (symbol, range) => {
      if (fail) throw new ApiError("I couldn't load price history right now. Please try again.", 502, true);
      return makeHistory({ symbol, name: "Nifty 50", range });
    });
    const retry = await screen.findByRole("button", { name: "Try again" });
    expect(fn).toHaveBeenCalledTimes(1);
    fail = false;
    await userEvent.click(retry);
    expect(await screen.findByRole("heading", { name: "Nifty 50" })).toBeInTheDocument();
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it("does not offer it when the request was wrong", async () => {
    setup(async () => { throw new ApiError("Unsupported symbol.", 422, false); });
    await screen.findByRole("alert");
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("a non-API failure still shows something kind", async () => {
    setup(async () => { throw new Error("boom"); });
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong. Please try again.");
  });

  it("choosing something else after an error loads it", async () => {
    setup(async (symbol, range) => {
      if (symbol === "NIFTY50") throw new ApiError("down", 502, true);
      return makeHistory({ symbol, name: symbol, range });
    });
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    expect(await screen.findByRole("heading", { name: "TCS" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("a slow answer for an earlier choice never overwrites a newer one", async () => {
    const pending: Record<string, (h: MarketHistory) => void> = {};
    setup((symbol, range) => new Promise((resolve) => { pending[symbol] = (h) => resolve({ ...h, symbol, range }); }));
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    await userEvent.click(screen.getByRole("button", { name: "Sensex" }));
    pending["SENSEX"](makeHistory({ name: "Sensex" }));
    expect(await screen.findByRole("heading", { name: "Sensex" })).toBeInTheDocument();
    pending["TCS"](makeHistory({ name: "TCS" }));
    pending["NIFTY50"](makeHistory({ name: "Nifty 50" }));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.getByRole("heading", { name: "Sensex" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "TCS" })).toBeNull();
  });

  it("an error for an earlier choice never replaces a newer chart", async () => {
    const pending: Record<string, { ok: (h: MarketHistory) => void; fail: (e: Error) => void }> = {};
    setup((symbol) => new Promise((resolve, reject) => { pending[symbol] = { ok: resolve, fail: reject }; }));
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    pending["TCS"].ok(makeHistory({ name: "TCS" }));
    await screen.findByRole("heading", { name: "TCS" });
    pending["NIFTY50"].fail(new ApiError("late failure", 502, true));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByRole("heading", { name: "TCS" })).toBeInTheDocument();
  });

  it("shows loading while the next choice loads, not the old chart", async () => {
    let release!: (h: MarketHistory) => void;
    setup((symbol) => (symbol === "NIFTY50" ? Promise.resolve(makeHistory({ name: "Nifty 50" })) : new Promise((r) => (release = r))));
    await screen.findByRole("heading", { name: "Nifty 50" });
    await userEvent.click(screen.getByRole("button", { name: "TCS" }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading prices…");
    expect(screen.queryByRole("heading", { name: "Nifty 50" })).toBeNull();
    release(makeHistory({ name: "TCS" }));
    await screen.findByRole("heading", { name: "TCS" });
  });
});
