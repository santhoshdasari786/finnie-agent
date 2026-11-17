import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

beforeEach(() => {
  // Tests marked `@vitest-environment node` (the live contract test) have no browser storage.
  if (typeof sessionStorage !== "undefined") sessionStorage.clear();
});
