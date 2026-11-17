import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tabs, panelId, tabId } from "./Tabs";

const tabs = [{ id: "chat", label: "Chat" }, { id: "portfolio", label: "Portfolio" }, { id: "market", label: "Market" }, { id: "goals", label: "Goals" }];

function setup(active = "chat") {
  const onChange = vi.fn();
  render(<Tabs tabs={tabs} active={active} onChange={onChange} />);
  return onChange;
}

describe("Tabs", () => {
  it("is a tab list with one tab per section, in order", () => {
    setup();
    expect(screen.getByRole("tablist", { name: "Sections" })).toBeInTheDocument();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Chat", "Portfolio", "Market", "Goals"]);
  });

  it("marks only the active tab as selected", () => {
    setup("market");
    expect(screen.getAllByRole("tab").map((t) => t.getAttribute("aria-selected"))).toEqual(["false", "false", "true", "false"]);
  });

  it("only the active tab is in the tab order", () => {
    setup("portfolio");
    expect(screen.getAllByRole("tab").map((t) => t.getAttribute("tabindex"))).toEqual(["-1", "0", "-1", "-1"]);
  });

  it("tells the panel it controls, by id", () => {
    setup();
    const tab = screen.getByRole("tab", { name: "Goals" });
    expect(tab).toHaveAttribute("id", tabId("goals"));
    expect(tab).toHaveAttribute("aria-controls", panelId("goals"));
    expect(tabId("goals")).not.toBe(panelId("goals"));
  });

  it("changes section on click", async () => {
    const onChange = setup();
    await userEvent.click(screen.getByRole("tab", { name: "Market" }));
    expect(onChange).toHaveBeenCalledWith("market");
  });

  it("moves right and wraps with the arrow keys", () => {
    const onChange = setup("goals");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Goals" }), { key: "ArrowRight" });
    expect(onChange).toHaveBeenLastCalledWith("chat");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Goals" }), { key: "ArrowLeft" });
    expect(onChange).toHaveBeenLastCalledWith("market");
  });

  it("wraps to the end from the first tab", () => {
    const onChange = setup("chat");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Chat" }), { key: "ArrowLeft" });
    expect(onChange).toHaveBeenLastCalledWith("goals");
  });

  it("jumps with Home and End", () => {
    const onChange = setup("market");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Market" }), { key: "End" });
    expect(onChange).toHaveBeenLastCalledWith("goals");
    fireEvent.keyDown(screen.getByRole("tab", { name: "Market" }), { key: "Home" });
    expect(onChange).toHaveBeenLastCalledWith("chat");
  });

  it("stops the page from scrolling when it handles an arrow key, and only then", () => {
    setup();
    expect(fireEvent.keyDown(screen.getByRole("tab", { name: "Chat" }), { key: "ArrowRight" })).toBe(false);
    expect(fireEvent.keyDown(screen.getByRole("tab", { name: "Chat" }), { key: "a" })).toBe(true);
  });

  it("ignores other keys", () => {
    const onChange = setup();
    fireEvent.keyDown(screen.getByRole("tab", { name: "Chat" }), { key: "a" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("moves focus along with the selection", () => {
    const onChange = vi.fn();
    const { rerender } = render(<Tabs tabs={tabs} active="chat" onChange={onChange} />);
    fireEvent.keyDown(screen.getByRole("tab", { name: "Chat" }), { key: "ArrowRight" });
    rerender(<Tabs tabs={tabs} active="portfolio" onChange={onChange} />);
    expect(screen.getByRole("tab", { name: "Portfolio" })).toHaveFocus();
  });
});
