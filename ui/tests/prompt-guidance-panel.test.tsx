import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { PromptGuidancePanel } from "@/components/prompt-guidance-panel"

beforeEach(() => {
  window.localStorage.clear()
})

describe("PromptGuidancePanel", () => {
  it("shows a placeholder when no role is selected yet", () => {
    render(<PromptGuidancePanel role={null} />)
    expect(screen.getByText(/select a role above/i)).toBeInTheDocument()
  })

  it("shows the contextual template for the selected role", () => {
    render(<PromptGuidancePanel role="system" />)
    expect(screen.getByRole("heading", { name: "System prompt" })).toBeInTheDocument()
    expect(screen.getByText("Identity")).toBeInTheDocument()
    expect(screen.queryByText("Instructions")).not.toBeInTheDocument()
  })

  it("swaps content when the role changes", () => {
    const { rerender } = render(<PromptGuidancePanel role="system" />)
    expect(screen.getByRole("heading", { name: "System prompt" })).toBeInTheDocument()

    rerender(<PromptGuidancePanel role="user" />)
    expect(screen.getByRole("heading", { name: "User prompt" })).toBeInTheDocument()
  })

  it("collapses and reopens", async () => {
    const user = userEvent.setup()
    render(<PromptGuidancePanel role="system" />)

    await user.click(screen.getByRole("button", { name: "Hide writing guide" }))
    expect(screen.queryByRole("heading", { name: "System prompt" })).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Show writing guide" }))
    expect(screen.getByRole("heading", { name: "System prompt" })).toBeInTheDocument()
  })

  it("copies a section's example to the clipboard", async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    // jsdom's Navigator.clipboard is a getter-only accessor, and user-event's own
    // setup() installs its own clipboard stub — override after setup() so ours wins.
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    })
    render(<PromptGuidancePanel role="system" />)

    await user.click(screen.getByRole("button", { name: "Copy Identity example" }))

    expect(writeText).toHaveBeenCalledWith(
      "You are a senior customer support agent for Acme Corp."
    )
  })
})
