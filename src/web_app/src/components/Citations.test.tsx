import { render, screen } from "@testing-library/react";
import type { Citation } from "../api/types";
import { Citations } from "./Citations";

const cite = (over: Partial<Citation> = {}): Citation => ({
  source: "https://example.org/a", title: "Capital Gains Basics", excerpt: "The Hindu, 13 Nov", verified_at: "2026-11-13", ...over,
});

describe("Citations", () => {
  it("shows a numbered chip per citation", () => {
    render(<Citations citations={[cite(), cite({ title: "Second", source: "https://example.org/b" })]} />);
    expect(screen.getByText(/\[1\]/)).toBeInTheDocument();
    expect(screen.getByText(/\[2\]/)).toBeInTheDocument();
  });

  it("links a web source and opens it safely in a new tab", () => {
    render(<Citations citations={[cite()]} />);
    const link = screen.getByRole("link", { name: /Capital Gains Basics/ });
    expect(link).toHaveAttribute("href", "https://example.org/a");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows the excerpt as a tooltip", () => {
    render(<Citations citations={[cite()]} />);
    expect(screen.getByRole("link")).toHaveAttribute("title", expect.stringContaining("The Hindu, 13 Nov"));
  });

  it("does not link a source that is only a title", () => {
    render(<Citations citations={[cite({ source: "Capital Gains Tax Basics in India" })]} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText(/Capital Gains Basics/)).toBeInTheDocument();
  });

  it("never links a javascript: source", () => {
    render(<Citations citations={[cite({ source: "javascript:alert(1)" })]} />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("never links a data: source", () => {
    render(<Citations citations={[cite({ source: "data:text/html,<script>alert(1)</script>" })]} />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("renders nothing without citations", () => {
    const { container } = render(<Citations citations={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
