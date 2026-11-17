import { render, screen, within } from "@testing-library/react";
import { LineChart } from "./LineChart";

const pts = (ys: number[]) => ys.map((y, i) => ({ x: i, y }));
const money = (n: number) => `₹${n}`;

/** The y values (second number of every pair) in an SVG path, in drawing order. */
const ysOf = (d: string) => [...d.matchAll(/[ML]\s*(-?[\d.]+)\s+(-?[\d.]+)/g)].map((m) => Number(m[2]));
const xsOf = (d: string) => [...d.matchAll(/[ML]\s*(-?[\d.]+)\s+(-?[\d.]+)/g)].map((m) => Number(m[1]));

const base = { ariaLabel: "Price chart", formatY: money };

describe("LineChart", () => {
  it("is an image named by the caller", () => {
    render(<LineChart {...base} series={[{ name: "A", points: pts([1, 2, 3]) }]} />);
    expect(screen.getByRole("img", { name: "Price chart" })).toBeInTheDocument();
  });

  it("draws one line per series, named", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: pts([1, 2]) }, { name: "B", points: pts([2, 3]) }]} />);
    expect([...container.querySelectorAll("[data-series]")].map((p) => p.getAttribute("data-series"))).toEqual(["A", "B"]);
  });

  it("draws a point per value, left to right", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: pts([1, 2, 3, 4]) }]} />);
    const d = container.querySelector("[data-series]")!.getAttribute("d")!;
    const xs = xsOf(d);
    expect(xs).toHaveLength(4);
    expect(xs).toEqual([...xs].sort((a, b) => a - b));
    expect(new Set(xs).size).toBe(4);
  });

  it("draws bigger values higher up (smaller SVG y)", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: pts([10, 30, 20]) }]} />);
    const ys = ysOf(container.querySelector("[data-series]")!.getAttribute("d")!);
    expect(ys[1]).toBeLessThan(ys[2]);
    expect(ys[2]).toBeLessThan(ys[0]);
  });

  it("labels the lowest, the middle and the highest value on the y axis", () => {
    render(<LineChart {...base} series={[{ name: "A", points: pts([100, 150, 200]) }]} />);
    const axis = screen.getByTestId("y-axis");
    expect(within(axis).getAllByText(/₹/).map((e) => e.textContent)).toEqual(["₹200", "₹150", "₹100"]);
  });

  it("labels the first and the last x value", () => {
    render(<LineChart {...base} formatX={(x) => `Year ${x}`} series={[{ name: "A", points: pts([1, 2, 3, 4, 5]) }]} />);
    const axis = screen.getByTestId("x-axis");
    expect(within(axis).getByText("Year 0")).toBeInTheDocument();
    expect(within(axis).getByText("Year 4")).toBeInTheDocument();
  });

  it("scales all series on the same axes", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "low", points: pts([0, 10]) }, { name: "high", points: pts([0, 100]) }]} />);
    const [low, high] = [...container.querySelectorAll("[data-series]")].map((p) => ysOf(p.getAttribute("d")!));
    expect(low[1]).toBeGreaterThan(high[1]);
    expect(within(screen.getByTestId("y-axis")).getByText("₹100")).toBeInTheDocument();
  });

  it("shows a reference line with its label and makes room for it", () => {
    render(<LineChart {...base} series={[{ name: "A", points: pts([0, 50]) }]} refLine={{ y: 500, label: "Target ₹500" }} />);
    expect(screen.getByTestId("ref-line")).toBeInTheDocument();
    expect(screen.getByText("Target ₹500")).toBeInTheDocument();
    expect(within(screen.getByTestId("y-axis")).getByText("₹500")).toBeInTheDocument();
  });

  it("draws the reference line at its own height", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: pts([0, 100]) }]} refLine={{ y: 50, label: "half" }} />);
    const line = screen.getByTestId("ref-line");
    const y = Number(line.getAttribute("y1"));
    const [first, last] = ysOf(container.querySelector("[data-series]")!.getAttribute("d")!);
    expect(y).toBeCloseTo((first + last) / 2, 1);
    expect(line.getAttribute("y2")).toBe(line.getAttribute("y1"));
  });

  it("has a legend when there is more than one line, and not for one", () => {
    const { rerender } = render(<LineChart {...base} series={[{ name: "Expected 7%", points: pts([1, 2]) }, { name: "Optimistic 11%", points: pts([1, 3]) }]} />);
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(within(legend).getAllByRole("listitem").map((i) => i.textContent)).toEqual(["Expected 7%", "Optimistic 11%"]);
    rerender(<LineChart {...base} series={[{ name: "Only", points: pts([1, 2]) }]} />);
    expect(screen.queryByRole("list", { name: "Legend" })).toBeNull();
  });

  it("colours a rising line green and a falling one red when told the tone", () => {
    const { container, rerender } = render(<LineChart {...base} series={[{ name: "A", tone: "up", points: pts([1, 2]) }]} />);
    expect(container.querySelector("[data-series]")!.getAttribute("class")).toMatch(/emerald/);
    rerender(<LineChart {...base} series={[{ name: "A", tone: "down", points: pts([2, 1]) }]} />);
    expect(container.querySelector("[data-series]")!.getAttribute("class")).toMatch(/red/);
  });

  it("gives several lines different colours", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: pts([1, 2]) }, { name: "B", points: pts([2, 3]) }]} />);
    const [a, b] = [...container.querySelectorAll("[data-series]")];
    expect(a.getAttribute("class")).not.toBe(b.getAttribute("class"));
  });

  it("draws a flat line in the middle rather than failing", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: pts([5, 5, 5]) }]} />);
    const ys = ysOf(container.querySelector("[data-series]")!.getAttribute("d")!);
    expect(new Set(ys).size).toBe(1);
    expect(ys.every(Number.isFinite)).toBe(true);
  });

  it("gives a flat line three different axis labels, not three copies of one", () => {
    render(<LineChart {...base} series={[{ name: "A", points: pts([100, 100, 100]) }]} />);
    const labels = within(screen.getByTestId("y-axis")).getAllByText(/₹/).map((e) => e.textContent);
    expect(labels).toHaveLength(3);
    expect(new Set(labels).size).toBe(3);
  });

  it("leaves out points that are not numbers", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "A", points: [{ x: 0, y: 1 }, { x: 1, y: Number.NaN }, { x: 2, y: 3 }] }]} />);
    expect(ysOf(container.querySelector("[data-series]")!.getAttribute("d")!)).toHaveLength(2);
  });

  it("says so when there are not enough points", () => {
    render(<LineChart {...base} series={[{ name: "A", points: pts([1]) }]} />);
    expect(screen.getByText("Not enough data to draw a chart.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("says so when there are no series", () => {
    render(<LineChart {...base} series={[]} />);
    expect(screen.getByText("Not enough data to draw a chart.")).toBeInTheDocument();
  });

  it("still draws a series that has enough points when another does not", () => {
    const { container } = render(<LineChart {...base} series={[{ name: "short", points: pts([1]) }, { name: "ok", points: pts([1, 2]) }]} />);
    expect([...container.querySelectorAll("[data-series]")].map((p) => p.getAttribute("data-series"))).toEqual(["ok"]);
  });
});
