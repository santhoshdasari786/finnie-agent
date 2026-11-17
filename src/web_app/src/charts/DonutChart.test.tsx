import { render, screen, within } from "@testing-library/react";
import { DonutChart } from "./DonutChart";

const slices = [{ label: "Equity", value: 60 }, { label: "Gold", value: 40 }];

describe("DonutChart", () => {
  it("is an image with the title and every share in its name, for screen readers", () => {
    render(<DonutChart title="Allocation" slices={slices} />);
    expect(screen.getByRole("img", { name: "Allocation: Equity 60.0%, Gold 40.0%" })).toBeInTheDocument();
  });

  it("lists each slice with its share in a legend", () => {
    render(<DonutChart title="Allocation" slices={slices} />);
    const items = within(screen.getByRole("list", { name: "Allocation legend" })).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Equity");
    expect(items[0]).toHaveTextContent("60.0%");
    expect(items[1]).toHaveTextContent("Gold 40.0%");
  });

  it("works out shares from the values, which need not add up to 100", () => {
    render(<DonutChart title="T" slices={[{ label: "A", value: 30 }, { label: "B", value: 10 }]} />);
    expect(screen.getByRole("img", { name: "T: A 75.0%, B 25.0%" })).toBeInTheDocument();
  });

  it("draws one arc per slice, sized by its share", () => {
    const { container } = render(<DonutChart title="T" slices={slices} />);
    const arcs = container.querySelectorAll("[data-slice]");
    expect(arcs).toHaveLength(2);
    expect(arcs[0]).toHaveAttribute("data-fraction", "0.6");
    expect(arcs[1]).toHaveAttribute("data-fraction", "0.4");
  });

  it("the arcs together cover the whole ring", () => {
    const { container } = render(<DonutChart title="T" slices={[{ label: "A", value: 1 }, { label: "B", value: 1 }, { label: "C", value: 1 }]} />);
    const total = [...container.querySelectorAll("[data-slice]")].reduce((s, el) => s + Number(el.getAttribute("data-fraction")), 0);
    expect(total).toBeCloseTo(1, 6);
  });

  it("starts each arc where the previous one ended", () => {
    const { container } = render(<DonutChart title="T" slices={slices} />);
    const [a, b] = [...container.querySelectorAll("[data-slice]")];
    expect(a.getAttribute("stroke-dashoffset")).toBe("0");
    const circumference = Number(a.getAttribute("stroke-dasharray")!.split(" ")[1]);
    expect(Number(b.getAttribute("stroke-dashoffset"))).toBeCloseTo(-0.6 * circumference, 1);
  });

  it("gives neighbouring slices different colours", () => {
    const { container } = render(<DonutChart title="T" slices={slices} />);
    const [a, b] = [...container.querySelectorAll("[data-slice]")];
    expect(a.getAttribute("class")).not.toBe(b.getAttribute("class"));
  });

  it("skips slices that are zero, negative or not numbers", () => {
    render(<DonutChart title="T" slices={[{ label: "A", value: 50 }, { label: "Z", value: 0 }, { label: "N", value: -5 }, { label: "X", value: Number.NaN }]} />);
    expect(screen.getByRole("img", { name: "T: A 100.0%" })).toBeInTheDocument();
    expect(screen.queryByText("Z")).toBeNull();
  });

  it("says so when there is nothing to draw", () => {
    render(<DonutChart title="T" slices={[]} />);
    expect(screen.getByText("No data to chart.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("copes with more slices than it has colours", () => {
    const many = Array.from({ length: 12 }, (_, i) => ({ label: `S${i}`, value: 1 }));
    const { container } = render(<DonutChart title="T" slices={many} />);
    expect(container.querySelectorAll("[data-slice]")).toHaveLength(12);
  });

  it("can show a label in the middle", () => {
    render(<DonutChart title="T" slices={slices} center="₹1M" />);
    expect(screen.getByText("₹1M")).toBeInTheDocument();
  });

  it("keeps the order it was given", () => {
    render(<DonutChart title="T" slices={[{ label: "B", value: 1 }, { label: "A", value: 9 }]} />);
    expect(screen.getByRole("img")).toHaveAccessibleName("T: B 10.0%, A 90.0%");
  });

  it("turns an underscore in a label into a space", () => {
    render(<DonutChart title="T" slices={[{ label: "fixed_income", value: 1 }]} />);
    expect(screen.getByText("fixed income")).toBeInTheDocument();
  });
});
