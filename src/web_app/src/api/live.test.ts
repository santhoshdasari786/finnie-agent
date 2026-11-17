// @vitest-environment node
/**
 * Contract test against a RUNNING server. Skipped unless LIVE_API is set:
 *   LIVE_API=http://localhost:8000 npm test -- live
 * It checks that what the real API sends is what these TypeScript types promise.
 */
import { createApi } from "./client";
import type { ChatResponse } from "./types";

const base = process.env.LIVE_API;
const live = describe.skipIf(!base);
if (base) vi.setConfig({ testTimeout: 120_000 }); // each test makes real model calls

live("the real API", () => {
  const api = createApi(base!, undefined, 120_000);
  const statuses = ["ok", "no_source", "clarify", "redirect", "needs_login", "error"];

  function checkShape(r: ChatResponse) {
    expect(statuses).toContain(r.status);
    expect(r.thread_id).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
    expect(typeof r.text).toBe("string");
    expect(r.text.length).toBeGreaterThan(0);
    expect(r.disclaimer.length).toBeGreaterThan(0);
    expect(Array.isArray(r.citations)).toBe(true);
    for (const c of r.citations) {
      expect(typeof c.source).toBe("string");
      expect(typeof c.title).toBe("string");
      expect(typeof c.excerpt).toBe("string");
    }
    expect(r.data === null || typeof r.data === "object").toBe(true);
    expect(typeof r.meta).toBe("object");
    expect(Object.keys(r.meta).every((k) => ["retryable", "awaiting", "missing"].includes(k))).toBe(true);
    expect(r.login_url === null || typeof r.login_url === "string").toBe(true);
  }

  it("lists the six agents", async () => {
    const list = await api.agents();
    expect(list.map((a) => a.name).sort()).toEqual(
      ["finance_qa", "goal_planning", "market_analysis", "news_synthesizer", "portfolio", "tax_education"],
    );
  });

  it("answers a concept question with the documented shape", async () => {
    const r = await api.chat({ message: "What is compound interest?" });
    checkShape(r);
    expect(r.agent).toBe("finance_qa");
  });

  it("keeps the conversation on one thread", async () => {
    const first = await api.chat({ message: "can I retire at 50?" });
    const second = await api.chat({ message: "I'm 35 and can save 20k a month", thread_id: first.thread_id });
    checkShape(second);
    expect(second.thread_id).toBe(first.thread_id);
    expect(second.agent).toBe("goal_planning");
    await api.endSession(first.thread_id);
  });

  it("returns a goal plan the panel can draw", async () => {
    const r = await api.chat({ message: "Can I reach 50 lakh in 10 years saving 20k a month?" });
    checkShape(r);
    const plan = (r.data as { plan?: { scenarios?: Array<Record<string, unknown>> } } | null)?.plan;
    expect(plan?.scenarios).toHaveLength(3);
    for (const s of plan!.scenarios!) {
      expect(typeof s.name).toBe("string");
      expect(typeof s.annual_rate_pct).toBe("number");
      expect(typeof s.projected).toBe("number");
    }
  });

  it("returns a portfolio the panel can draw", async () => {
    const id = "livecontract-portfolio";
    await api.chat({ message: "connect sample", thread_id: id });
    const r = await api.chat({ message: "analyze my portfolio", thread_id: id });
    checkShape(r);
    const m = (r.data as { metrics?: { total_value?: unknown; holdings?: Array<Record<string, unknown>> } } | null)?.metrics;
    expect(typeof m?.total_value).toBe("number");
    expect(m!.holdings!.length).toBeGreaterThan(0);
    expect(typeof m!.holdings![0].allocation_pct).toBe("number");
    await api.endSession(id);
  });

  it("offers the portfolio sources as options", async () => {
    const r = await api.chat({ message: "connect to my portfolio" });
    checkShape(r);
    expect(r.status).toBe("clarify");
    const options = (r.data as { options?: Array<{ name: string; label: string }> }).options!;
    expect(options.map((o) => o.name)).toContain("sample");
  });

  it("returns news citations with links", async () => {
    const r = await api.chat({ message: "latest news on Infosys" });
    checkShape(r);
    expect(r.agent).toBe("news_synthesizer");
    expect(r.citations.every((c) => /^https?:\/\//.test(c.source))).toBe(true);
  });

  it("returns a normal reply for a message the guard blocks", async () => {
    const r = await api.chat({ message: "I want to die" });
    checkShape(r);
    expect(r.agent).toBe("guard");
  });

  it("explains a bad request in words", async () => {
    await expect(api.chat({ message: "   " })).rejects.toMatchObject({ status: 422, retryable: false });
  });
});
