import { render, screen } from "@testing-library/react";
import { RichText } from "./RichText";

describe("RichText", () => {
  it("renders **bold** as strong text", () => {
    render(<RichText text="A **SIP** is regular investing" />);
    expect(screen.getByText("SIP").tagName).toBe("STRONG");
  });

  it("renders several bold parts in one line", () => {
    render(<RichText text="**one** and **two**" />);
    expect(screen.getAllByText(/one|two/).map((e) => e.tagName)).toEqual(["STRONG", "STRONG"]);
  });

  it("leaves an unmatched ** alone", () => {
    const { container } = render(<RichText text="5 ** 2 is a power" />);
    expect(container.querySelector("strong")).toBeNull();
    expect(container).toHaveTextContent("5 ** 2 is a power");
  });

  it("turns '- ' lines into a list", () => {
    render(<RichText text={"Scenarios:\n- Pessimistic: low\n- Expected: mid"} />);
    expect(screen.getByRole("list")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Scenarios:")).toBeInTheDocument();
  });

  it("renders bold inside a list item", () => {
    render(<RichText text="- **Key** point" />);
    expect(screen.getByText("Key").tagName).toBe("STRONG");
  });

  it("splits paragraphs on a blank line", () => {
    const { container } = render(<RichText text={"First part.\n\nSecond part."} />);
    expect(container.querySelectorAll("p")).toHaveLength(2);
  });

  it("keeps a single line break inside a paragraph", () => {
    const { container } = render(<RichText text={"line one\nline two"} />);
    expect(container.querySelector("p")?.textContent).toBe("line one\nline two");
  });

  it("shows HTML as plain text and never as markup", () => {
    const { container } = render(<RichText text={"<b>x</b> <script>alert(1)</script> <img src=x onerror=alert(1)>"} />);
    expect(container.querySelector("b, script, img")).toBeNull();
    expect(container).toHaveTextContent("<script>alert(1)</script>");
  });

  it("keeps [n] citation markers as text", () => {
    render(<RichText text="Profit rose [2]." />);
    expect(screen.getByText("Profit rose [2].")).toBeInTheDocument();
  });

  it("renders nothing for empty text", () => {
    const { container } = render(<RichText text="" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("RichText layout", () => {
  it("asks the browser to keep line breaks", () => {
    const { container } = render(<RichText text={"a\nb"} />);
    expect(container.querySelector("p")).toHaveClass("whitespace-pre-line");
  });
});
