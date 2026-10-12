import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the symptom assessment introduction", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Symptom assessment" }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(/does not provide a medical diagnosis/i),
    ).toBeInTheDocument();
  });
});
