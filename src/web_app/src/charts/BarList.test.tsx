import { render, screen, within } from "@testing-library/react";
import { BarList } from "./BarList";

const items = [{ label: "TCS", value: 40 }, { label: "INFY", value: 25.5 }, { label: "GOLDBEES", value: 10 }];

describe("BarList", () => {
  it("is a list with a name and a row per item, in order", () => {
    render(<BarList title="Holdings by share" items={items} />);
    const rows = within(screen.getByRole("list", { name: "Holdings by share" })).getAllByRole("listitem");
    expect(rows.map((r) => r.textContent)).toEqual(["TCS40.0%", "INFY25.5%", "GOLDBEES10.0%"]);
  });

  it("sizes each bar by its value out of 100", () => {
    const { container } = render(<BarList title="T" items={items} />);
    const widths = [...container.querySelectorAll("[data-bar]")].map((b) => (b as HTMLElement).style.width);
    expect(widths).toEqual(["40%", "25.5%", "10%"]);
  });

  it("can be scaled to a different maximum", () => {
    const { container } = render(<BarList title="T" items={[{ label: "A", value: 5 }]} max={10} />);
    expect((container.querySelector("[data-bar]") as HTMLElement).style.width).toBe("50%");
  });

  it("never draws a bar longer than the track or shorter than nothing", () => {
    const { container } = render(<BarList title="T" items={[{ label: "A", value: 250 }, { label: "B", value: -3 }]} />);
    const widths = [...container.querySelectorAll("[data-bar]")].map((b) => (b as HTMLElement).style.width);
    expect(widths).toEqual(["100%", "0%"]);
  });

  it("formats the value the caller's way", () => {
    render(<BarList title="T" items={[{ label: "A", value: 12.345 }]} format={(v) => `${v.toFixed(0)} pts`} />);
    expect(screen.getByText("12 pts")).toBeInTheDocument();
  });

  it("skips items whose value is not a number", () => {
    render(<BarList title="T" items={[{ label: "A", value: Number.NaN }, { label: "B", value: 5 }]} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("says so when there is nothing to draw", () => {
    render(<BarList title="T" items={[]} />);
    expect(screen.getByText("No data to chart.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });
});
