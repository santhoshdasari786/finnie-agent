import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Composer } from "./Composer";

describe("Composer", () => {
  it("sends the text with the button and clears the box", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} disabled={false} />);
    await userEvent.type(screen.getByRole("textbox"), "What is a SIP?");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(onSend).toHaveBeenCalledWith("What is a SIP?");
    expect(screen.getByRole("textbox")).toHaveValue("");
  });

  it("sends on Enter", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} disabled={false} />);
    await userEvent.type(screen.getByRole("textbox"), "hello{Enter}");
    expect(onSend).toHaveBeenCalledWith("hello");
  });

  it("adds a new line on Shift+Enter instead of sending", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} disabled={false} />);
    await userEvent.type(screen.getByRole("textbox"), "one{Shift>}{Enter}{/Shift}two");
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox")).toHaveValue("one\ntwo");
  });

  it("does not send a blank message", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} disabled={false} />);
    await userEvent.type(screen.getByRole("textbox"), "   {Enter}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables the Send button while the box is empty", () => {
    render(<Composer onSend={() => {}} disabled={false} />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("is disabled while an answer is pending", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("shows how many characters are left", async () => {
    render(<Composer onSend={() => {}} disabled={false} />);
    await userEvent.type(screen.getByRole("textbox"), "12345");
    expect(screen.getByText("5 / 2000")).toBeInTheDocument();
  });

  it("stops at the server's limit", () => {
    render(<Composer onSend={() => {}} disabled={false} />);
    expect(screen.getByRole("textbox")).toHaveAttribute("maxlength", "2000");
  });

  it("has an accessible name", () => {
    render(<Composer onSend={() => {}} disabled={false} />);
    expect(screen.getByRole("textbox", { name: /message/i })).toBeInTheDocument();
  });
});

describe("Composer when disabled", () => {
  it("ignores a form submit too", () => {
    const onSend = vi.fn();
    const { container } = render(<Composer onSend={onSend} disabled />);
    fireEvent.submit(container.querySelector("form")!);
    expect(onSend).not.toHaveBeenCalled();
  });
});

describe("Composer disabled after typing", () => {
  it("does not send text typed before it was disabled", async () => {
    const onSend = vi.fn();
    const { container, rerender } = render(<Composer onSend={onSend} disabled={false} />);
    await userEvent.type(screen.getByRole("textbox"), "typed before");
    rerender(<Composer onSend={onSend} disabled />);
    fireEvent.submit(container.querySelector("form")!);
    expect(onSend).not.toHaveBeenCalled();
  });
});
