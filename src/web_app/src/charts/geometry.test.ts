import { donutSlices, extent, linePath, padDomain, scaleLinear, type Box } from "./geometry";

const box: Box = { width: 100, height: 50, left: 10, right: 10, top: 5, bottom: 5 };

describe("extent", () => {
  it("is the smallest and the largest value", () => {
    expect(extent([3, 1, 2, 9, -4])).toEqual([-4, 9]);
  });
  it("is [0, 0] for nothing", () => {
    expect(extent([])).toEqual([0, 0]);
  });
});

describe("padDomain (a flat line still needs a visible range)", () => {
  it("leaves a real range alone", () => {
    expect(padDomain([10, 20])).toEqual([10, 20]);
  });
  it("opens a flat range by a share of its value", () => {
    expect(padDomain([100, 100])).toEqual([95, 105]);
  });
  it("opens a flat range at zero by one", () => {
    expect(padDomain([0, 0])).toEqual([-1, 1]);
  });
  it("uses the size of a negative value", () => {
    expect(padDomain([-100, -100])).toEqual([-105, -95]);
  });
});

describe("scaleLinear", () => {
  it("maps the ends and the middle", () => {
    const s = scaleLinear([0, 10], [100, 200]);
    expect([s(0), s(5), s(10)]).toEqual([100, 150, 200]);
  });
  it("can run backwards (SVG y grows downward)", () => {
    const s = scaleLinear([0, 100], [45, 5]);
    expect([s(0), s(100), s(50)]).toEqual([45, 5, 25]);
  });
  it("puts everything in the middle of a degenerate domain", () => {
    expect(scaleLinear([7, 7], [0, 10])(7)).toBe(5);
  });
});

describe("linePath", () => {
  it("starts with M, continues with L, and flips y", () => {
    expect(linePath([{ x: 0, y: 0 }, { x: 10, y: 100 }], [0, 10], [0, 100], box)).toBe("M10 45 L90 5");
  });
  it("draws every point in order", () => {
    const d = linePath([{ x: 0, y: 0 }, { x: 5, y: 50 }, { x: 10, y: 100 }], [0, 10], [0, 100], box);
    expect(d).toBe("M10 45 L50 25 L90 5");
  });
  it("rounds to two decimals", () => {
    const d = linePath([{ x: 0, y: 0 }, { x: 1, y: 1 }, { x: 3, y: 3 }], [0, 3], [0, 3], box);
    expect(d).toBe("M10 45 L36.67 31.67 L90 5");
  });
  it("is empty with no points", () => {
    expect(linePath([], [0, 1], [0, 1], box)).toBe("");
  });
});

describe("donutSlices", () => {
  it("gives each value its share and where it starts", () => {
    expect(donutSlices([50, 30, 20])).toEqual([
      { fraction: 0.5, offset: 0 }, { fraction: 0.3, offset: 0.5 }, { fraction: 0.2, offset: 0.8 },
    ]);
  });
  it("does not need the values to add up to 100", () => {
    expect(donutSlices([3, 1])).toEqual([{ fraction: 0.75, offset: 0 }, { fraction: 0.25, offset: 0.75 }]);
  });
  it("is empty when the total is zero", () => {
    expect(donutSlices([0, 0])).toEqual([]);
    expect(donutSlices([])).toEqual([]);
  });
});
