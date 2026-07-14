import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { http, HttpResponse } from "msw"
import { server } from "./mocks/server"
import { PromptList } from "@/components/prompt-list"

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}))

const API_URL = "http://localhost:8000"

const ONE_PROMPT = [
  {
    id: "prompt-1",
    slug: "/sales/alpha",
    leaf_slug: "alpha",
    category_id: "cat-1",
    version: 1,
    created_at: "2026-01-15T00:00:00Z",
  },
]

function renderList() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <PromptList />
    </QueryClientProvider>
  )
}

describe("PromptList", () => {
  it("shows an empty state with a New prompt link when there are no prompts", async () => {
    renderList()

    await waitFor(() => {
      expect(screen.getByText("No prompts yet")).toBeInTheDocument()
    })
    const links = screen.getAllByRole("link", { name: "New prompt" })
    expect(links.length).toBeGreaterThan(0)
    for (const link of links) {
      expect(link).toHaveAttribute("href", "/prompts/new")
    }
  })

  it("renders one row per prompt with Slug and Created columns", async () => {
    server.use(
      http.get(`${API_URL}/prompts`, () =>
        HttpResponse.json([
          {
            id: "1",
            slug: "/sales/alpha",
            leaf_slug: "alpha",
            category_id: "cat-1",
            version: 1,
            created_at: "2026-01-15T00:00:00Z",
          },
          {
            id: "2",
            slug: "/sales/zeta",
            leaf_slug: "zeta",
            category_id: "cat-1",
            version: 2,
            created_at: "2026-02-20T00:00:00Z",
          },
        ])
      )
    )

    renderList()

    const rows = await screen.findAllByRole("row")
    // First row is the header.
    expect(rows).toHaveLength(3)
    expect(within(rows[1]).getByText("/sales/alpha")).toBeInTheDocument()
    expect(within(rows[2]).getByText("/sales/zeta")).toBeInTheDocument()
    expect(screen.queryByText("No prompts yet")).not.toBeInTheDocument()

    expect(within(rows[1]).getByRole("link", { name: "Edit" })).toHaveAttribute(
      "href",
      "/prompts/edit/sales/alpha"
    )
    expect(within(rows[2]).getByRole("link", { name: "Edit" })).toHaveAttribute(
      "href",
      "/prompts/edit/sales/zeta"
    )
  })
})

describe("PromptList delete", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("deletes a prompt via the confirm dialog and shows a success toast", async () => {
    server.use(
      http.get(`${API_URL}/prompts`, () => HttpResponse.json(ONE_PROMPT)),
      http.delete(`${API_URL}/prompt/prompt-1`, () =>
        HttpResponse.json({
          id: "prompt-2",
          slug: "/sales/alpha",
          leaf_slug: "alpha",
          category_id: "cat-1",
          version: 2,
          role: "user",
          text: "",
          is_deleted: true,
          created_at: "2026-01-16T00:00:00Z",
        })
      )
    )

    const user = userEvent.setup()
    renderList()

    const row = (await screen.findByText("/sales/alpha")).closest("tr")!
    await user.click(within(row).getByRole("button", { name: "Delete" }))

    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Delete" }))

    const { toast } = await import("sonner")
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Prompt deleted")
    })
  })

  it("shows an error toast and does not silently retry when the row is stale (409)", async () => {
    server.use(
      http.get(`${API_URL}/prompts`, () => HttpResponse.json(ONE_PROMPT)),
      http.delete(`${API_URL}/prompt/prompt-1`, () =>
        HttpResponse.json(
          { detail: "this version is no longer the current version; re-read it and retry" },
          { status: 409 }
        )
      )
    )

    const user = userEvent.setup()
    renderList()

    const row = (await screen.findByText("/sales/alpha")).closest("tr")!
    await user.click(within(row).getByRole("button", { name: "Delete" }))

    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Delete" }))

    const { toast } = await import("sonner")
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("This prompt changed elsewhere — refreshing the list")
    })
  })
})
