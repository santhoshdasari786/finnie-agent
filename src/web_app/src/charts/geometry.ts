export type Domain = [number, number];

export interface Box {
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export function extent(values: number[]): Domain {
  if (!values.length) return [0, 0];
  return [Math.min(...values), Math.max(...values)];
}

/** A flat range (one value) has no height to draw, so open it up a little. */
export function padDomain([lo, hi]: Domain, ratio = 0.05): Domain {
  if (lo !== hi) return [lo, hi];
  const pad = Math.abs(lo) * ratio || 1;
  return [lo - pad, hi + pad];
}

export function scaleLinear([d0, d1]: Domain, [r0, r1]: Domain): (v: number) => number {
  return (v) => (d0 === d1 ? (r0 + r1) / 2 : r0 + ((v - d0) / (d1 - d0)) * (r1 - r0));
}

const round2 = (n: number) => Math.round(n * 100) / 100;

export function linePath(points: { x: number; y: number }[], xDomain: Domain, yDomain: Domain, box: Box): string {
  const sx = scaleLinear(xDomain, [box.left, box.width - box.right]);
  const sy = scaleLinear(yDomain, [box.height - box.bottom, box.top]);          // SVG y grows downward
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${round2(sx(p.x))} ${round2(sy(p.y))}`).join(" ");
}

export function donutSlices(values: number[]): { fraction: number; offset: number }[] {
  const total = values.reduce((a, b) => a + b, 0);
  if (!(total > 0)) return [];
  let before = 0;
  return values.map((v) => {
    const slice = { fraction: v / total, offset: before };
    before += slice.fraction;
    return slice;
  });
}
