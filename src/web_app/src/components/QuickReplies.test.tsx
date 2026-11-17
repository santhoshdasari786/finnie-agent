import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickReplies } from "./QuickReplies";

const data = { options: [
  { name: "sample", label: "Sample portfolio (demo data, no login)" },
  { name: "kite", label: "Zerodha Kite (live account, needs login)" },
], connected: [] };

describe("QuickReplies", () => {
  it("shows one button per portfolio source", () => {
    render(<QuickReplies data={data} onSend={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("sends the connect command for the source that was clicked", async () => {
    const onSend = vi.fn();
    render(<QuickReplies data={data} onSend={onSend} />);
    await userEvent.click(screen.getByRole("button", { name: /Sample portfolio/ }));
    expect(onSend).toHaveBeenCalledWith("connect sample");
    await userEvent.click(screen.getByRole("button", { name: /Zerodha Kite/ }));
    expect(onSend).toHaveBeenLastCalledWith("connect kite");
  });

  it("renders nothing without options", () => {
    const { container } = render(<QuickReplies data={null} onSend={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("ignores options that are not well formed", () => {
    render(<QuickReplies data={{ options: [{ name: 5 }, null, { name: "sample", label: "Sample" }, "x"] }} onSend={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  it("ignores options that are not a list", () => {
    const { container } = render(<QuickReplies data={{ options: "nope" }} onSend={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("does not turn an odd source name into a command", () => {
    const { container } = render(<QuickReplies data={{ options: [{ name: "kite; drop", label: "bad" }] }} onSend={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
