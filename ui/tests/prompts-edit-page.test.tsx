import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi } from "vitest"
import { http, HttpResponse } from "msw"
import { server } from "./mocks/server"
import EditPrompt from "@/app/prompts/edit/[...slug]/page"

const pushMock = vi.fn()
vi.mock("sonner", () => ({
  toast: { success: vi.fn() },
  Toaster: () => null,
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ slug: ["sales", "my-prompt"] }),
}))

function newQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function renderPage(queryClient: QueryClient = newQueryClient()) {
  return render(
    <QueryClientProvider client={queryClient}>
      <EditPrompt />
    </QueryClientProvider>
  )
}

// The Text field is a CodeMirror editor (contenteditable), not a native
// textarea — it exposes an accessible name via aria-label rather than
// label[for], and has no .value, so assertions use toHaveTextContent.
function textEditor() {
  return screen.getByRole("textbox", { name: "Text" })
}

describe("EditPrompt page", () => {
  it("resolves the Live Version by slug and renders it pre-filled", async () => {
    renderPage()

    await waitFor(() => {
      expect(textEditor()).toHaveTextContent("hello world")
    })
    expect(screen.getByLabelText("Prompt name")).toHaveValue("my-prompt")
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument()
  })

  it("shows a not-found state when the slug has no Live Version", async () => {
    server.use(
      http.get("http://localhost:8000/prompt", () =>
        HttpResponse.json({ detail: "slug has no live version" }, { status: 404 })
      )
    )

    renderPage()

    await waitFor(() => {
      expect(screen.getByText("This prompt no longer exists.")).toBeInTheDocument()
    })
  })
})

// Regression tests for the "edit, go back, edit again shows the old version" bug: the
// QueryClient persists across navigations in the real app (it's created once in
// app/providers.tsx), so these reuse a single client across an unmount + remount to
// reproduce that same cache lifetime, per ADR-0006.
describe("EditPrompt page (revisit after the Live Version changes)", () => {
  it("shows the freshly-saved text on revisit, not the pre-edit cache entry", async () => {
    const user = userEvent.setup()
    const queryClient = newQueryClient()

    const { unmount } = renderPage(queryClient)
    await waitFor(() => textEditor())

    await user.clear(textEditor())
    await user.type(textEditor(), "updated text")
    await user.click(screen.getByRole("button", { name: "Save changes" }))
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/"))

    // Simulate navigating back to "/" and clicking "Edit" again: same QueryClient,
    // a brand-new EditPrompt/PromptForm mount.
    unmount()
    renderPage(queryClient)

    await waitFor(() => {
      expect(textEditor()).toHaveTextContent("updated text")
    })
  })

  it("picks up a concurrent editor's change instead of getting stuck on a stale cache hit", async () => {
    const queryClient = newQueryClient()

    const { unmount } = renderPage(queryClient)
    await waitFor(() => textEditor())
    unmount()

    // Someone/something else updates the same slug directly against the backend,
    // bypassing this client's own mutation entirely (ADR-0003 concurrent editors).
    await fetch("http://localhost:8000/prompt/00000000-0000-0000-0000-000000000001", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "changed by someone else" }),
    })

    renderPage(queryClient)

    await waitFor(() => {
      expect(textEditor()).toHaveTextContent("changed by someone else")
    })
  })
})
