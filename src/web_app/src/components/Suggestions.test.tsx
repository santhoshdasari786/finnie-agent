import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SUGGESTIONS, Suggestions } from "./Suggestions";

describe("Suggestions", () => {
  it("offers a few ways to start", () => {
    render(<Suggestions onPick={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(SUGGESTIONS.length);
    expect(SUGGESTIONS.length).toBeGreaterThanOrEqual(4);
  });

  it("sends the suggestion that was clicked", async () => {
    const onPick = vi.fn();
    render(<Suggestions onPick={onPick} />);
    await userEvent.click(screen.getAllByRole("button")[0]);
    expect(onPick).toHaveBeenCalledWith(SUGGESTIONS[0]);
  });

  it("covers the agents a visitor would want to try", () => {
    const all = SUGGESTIONS.join(" ").toLowerCase();
    expect(all).toMatch(/sip|compound/);
    expect(all).toMatch(/tax|capital gains/);
    expect(all).toMatch(/retire|reach|goal/);
    expect(all).toMatch(/news/);
    expect(all).toMatch(/portfolio/);
  });

  it("keeps every suggestion within the message limit", () => {
    for (const s of SUGGESTIONS) expect(s.length).toBeLessThanOrEqual(200);
  });
});
