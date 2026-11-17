import { assistant, goalData, portfolioData, user } from "../test/factories";
import { latestWith, lastFrom } from "./latest";

describe("latestWith", () => {
  it("is null for no messages", () => {
    expect(latestWith([], "portfolio", "metrics")).toBeNull();
  });

  it("finds the newest reply from that agent that has the data", () => {
    const messages = [
      assistant({ agent: "portfolio", data: portfolioData({ total_value: 1 }) }, "a1"),
      user("again", "u2"),
      assistant({ agent: "portfolio", data: portfolioData({ total_value: 2 }) }, "a2"),
    ];
    const found = latestWith(messages, "portfolio", "metrics");
    expect((found?.data?.metrics as { total_value: number }).total_value).toBe(2);
  });

  it("skips a newer reply that has no such data", () => {
    const messages = [
      assistant({ agent: "portfolio", data: portfolioData() }, "a1"),
      assistant({ agent: "portfolio", status: "error", data: null }, "a2"),
    ];
    expect(latestWith(messages, "portfolio", "metrics")?.status).toBe("ok");
  });

  it("ignores other agents even when their data has the same key", () => {
    expect(latestWith([assistant({ agent: "finance_qa", data: portfolioData() })], "portfolio", "metrics")).toBeNull();
  });

  it("ignores user and error messages", () => {
    expect(latestWith([user("x"), { id: "e", role: "error", text: "no", retryText: null }], "goal_planning", "plan")).toBeNull();
  });

  it("works for goals", () => {
    expect(latestWith([assistant({ agent: "goal_planning", data: goalData() })], "goal_planning", "plan")).not.toBeNull();
  });

  it("needs the value to be an object, not a string or a list", () => {
    expect(latestWith([assistant({ agent: "portfolio", data: { metrics: "x" } })], "portfolio", "metrics")).toBeNull();
    expect(latestWith([assistant({ agent: "portfolio", data: { metrics: [1] } })], "portfolio", "metrics")).toBeNull();
  });
});

describe("lastFrom", () => {
  it("is the newest reply from the agent, whatever its status", () => {
    const messages = [
      assistant({ agent: "portfolio", status: "ok" }, "a1"),
      assistant({ agent: "finance_qa" }, "a2"),
      assistant({ agent: "portfolio", status: "needs_login" }, "a3"),
      assistant({ agent: "finance_qa" }, "a4"),
    ];
    expect(lastFrom(messages, "portfolio")?.status).toBe("needs_login");
  });

  it("is null when the agent has not answered", () => {
    expect(lastFrom([assistant({ agent: "finance_qa" })], "portfolio")).toBeNull();
    expect(lastFrom([], "portfolio")).toBeNull();
  });
});
