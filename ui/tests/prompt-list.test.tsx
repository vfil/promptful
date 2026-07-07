import { render, screen, waitFor, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect } from "vitest"
import { http, HttpResponse } from "msw"
import { server } from "./mocks/server"
import { PromptList } from "@/components/prompt-list"

const API_URL = "http://localhost:8000"

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
