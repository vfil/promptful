import { useState } from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect } from "vitest"
import { PromptTextEditor } from "@/components/prompt-text-editor"

function ControlledEditor({ initial = "" }: { initial?: string }) {
  const [value, setValue] = useState(initial)
  return <PromptTextEditor value={value} onChange={setValue} ariaLabel="Text" />
}

// user-event's `type()` treats { and } as special-key syntax; doubling each
// brace is how its docs say to type them literally — needed constantly here
// since Jinja2 tags are made of braces.
function literal(text: string): string {
  return text.replace(/[{}]/g, "$&$&")
}

describe("PromptTextEditor", () => {
  it("starts in Edit mode with an accessible textbox showing the initial value", () => {
    render(<ControlledEditor initial="hello" />)
    expect(screen.getByRole("textbox", { name: "Text" })).toHaveTextContent("hello")
  })

  it("types into the editor and reflects the new value", async () => {
    const user = userEvent.setup()
    render(<ControlledEditor />)

    await user.type(screen.getByRole("textbox", { name: "Text" }), literal("hi {{ name }}"))

    expect(screen.getByRole("textbox", { name: "Text" })).toHaveTextContent("hi {{ name }}")
  })

  it("highlights a well-formed Jinja2 tag and flags an unmatched one", async () => {
    const user = userEvent.setup()
    render(<ControlledEditor />)

    await user.type(
      screen.getByRole("textbox", { name: "Text" }),
      literal("{{ ok }} and {{ broken")
    )

    const editor = screen.getByRole("textbox", { name: "Text" })
    expect(editor.querySelectorAll(".cm-jinja2-tag").length).toBeGreaterThan(0)
    expect(editor.querySelectorAll(".cm-jinja2-tag-error").length).toBeGreaterThan(0)
  })

  it("switches to Preview and renders Markdown without executing Jinja2 tags", async () => {
    const user = userEvent.setup()
    render(<ControlledEditor initial={"# Heading\n\n{{ not_executed }}"} />)

    await user.click(screen.getByRole("button", { name: "Preview" }))

    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument()
    expect(screen.getByText(/\{\{ not_executed \}\}/)).toBeInTheDocument()
  })
})
