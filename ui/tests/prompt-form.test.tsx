import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { http, HttpResponse } from "msw"
import { server } from "./mocks/server"
import { PromptForm } from "@/components/prompt-form"

vi.mock("sonner", () => ({
  toast: { success: vi.fn() },
  Toaster: () => null,
}))

const pushMock = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

function renderForm(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe("PromptForm (create mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows success toast and redirects to the prompt list after successful create", async () => {
    const user = userEvent.setup()
    renderForm(<PromptForm mode="create" />)

    // Wait for categories to load, then open the Category combobox
    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    await user.click(screen.getByRole("combobox", { name: "Category" }))
    await user.click(await screen.findByText("/sales"))

    await user.type(screen.getByLabelText("Prompt name"), "my-prompt")
    await user.type(screen.getByLabelText("Text"), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    const { toast } = await import("sonner")
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Prompt created")
    })
    expect(pushMock).toHaveBeenCalledWith("/")
  })

  it("shows inline leaf-slug error on 409 conflict", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/create", () =>
        HttpResponse.json(
          {
            detail: "a prompt 'my-prompt' already exists in this category; use POST /prompt/{id} to update it",
          },
          { status: 409 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm(<PromptForm mode="create" />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    await user.click(screen.getByRole("combobox", { name: "Category" }))
    await user.click(await screen.findByText("/sales"))

    await user.type(screen.getByLabelText("Prompt name"), "my-prompt")
    await user.type(screen.getByLabelText("Text"), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("already exists in this category")
    })
    expect(screen.getByRole("alert").id).toBe("leaf-slug-error")
  })

  it("shows inline text error on 422 Jinja2 syntax failure", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/create", () =>
        HttpResponse.json(
          {
            detail: [
              {
                type: "value_error",
                loc: ["body", "text"],
                msg: "Value error, text is not a valid Jinja2 template: unexpected '}'",
                input: "{% bad %}",
                url: "",
              },
            ],
          },
          { status: 422 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm(<PromptForm mode="create" />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    await user.click(screen.getByRole("combobox", { name: "Category" }))
    await user.click(await screen.findByText("/sales"))

    await user.type(screen.getByLabelText("Prompt name"), "my-prompt")
    await user.type(screen.getByLabelText("Text"), "bad template")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "text is not a valid Jinja2 template"
      )
    })
    expect(screen.getByRole("alert").id).toBe("text-error")
  })

  it("shows inline leaf-slug error on 422 leaf_slug format failure", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/create", () =>
        HttpResponse.json(
          {
            detail: [
              {
                type: "value_error",
                loc: ["body", "leaf_slug"],
                msg: "Value error, leaf_slug must be lowercase letters, digits and hyphens only",
                input: "Bad/Slug",
                url: "",
              },
            ],
          },
          { status: 422 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm(<PromptForm mode="create" />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    await user.click(screen.getByRole("combobox", { name: "Category" }))
    await user.click(await screen.findByText("/sales"))

    await user.type(screen.getByLabelText("Prompt name"), "Bad/Slug")
    await user.type(screen.getByLabelText("Text"), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "leaf_slug must be lowercase letters"
      )
    })
    expect(screen.getByRole("alert").id).toBe("leaf-slug-error")
  })

  it("creates a new category inline and selects it", async () => {
    const user = userEvent.setup()
    renderForm(<PromptForm mode="create" />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    await user.click(screen.getByRole("combobox", { name: "Category" }))

    // Type a new slug_segment that doesn't exist yet
    await user.type(screen.getByPlaceholderText("Search or type slug…"), "engineering")

    // Click the "Create" option
    await user.click(await screen.findByText(/Create "engineering"/))

    // The newly created category should be selected
    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: "Category" })).toHaveTextContent("/engineering")
    })
  })
})

const UPDATE_PROPS = {
  mode: "update" as const,
  id: "00000000-0000-0000-0000-000000000001",
  slug: "/sales/my-prompt",
  leafSlug: "my-prompt",
  categoryId: "cat-00000000-0000-0000-0000-000000000001",
  initialText: "hello world",
}

describe("PromptForm (update mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("pre-fills text and disables Category/Parent category/Prompt name", async () => {
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    expect(screen.getByRole("combobox", { name: "Category" })).toBeDisabled()
    expect(screen.getByRole("combobox", { name: "Parent category" })).toBeDisabled()
    expect(screen.getByLabelText("Prompt name")).toBeDisabled()
    expect(screen.getByLabelText("Text")).toHaveValue("hello world")
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument()
  })

  it("shows success toast and redirects to the prompt list after successful update", async () => {
    const user = userEvent.setup()
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await user.clear(screen.getByLabelText("Text"))
    await user.type(screen.getByLabelText("Text"), "updated text")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    const { toast } = await import("sonner")
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Prompt updated")
    })
    expect(pushMock).toHaveBeenCalledWith("/")
  })

  it("shows a conflict banner on 409 and reloads the latest version on demand", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/:id", () =>
        HttpResponse.json(
          { detail: "this version is no longer the current version; re-read it and retry" },
          { status: 409 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await user.type(screen.getByLabelText("Text"), " more")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("changed elsewhere")
    })

    // The default GET /prompt?slug=... handler returns the Live Version's text.
    await user.click(screen.getByRole("button", { name: "Reload latest version" }))

    await waitFor(() => {
      expect(screen.getByLabelText("Text")).toHaveValue("hello world")
    })
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("shows inline text error on 422 Jinja2 syntax failure", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/:id", () =>
        HttpResponse.json(
          {
            detail: [
              {
                type: "value_error",
                loc: ["body", "text"],
                msg: "Value error, text is not a valid Jinja2 template: unexpected '}'",
                input: "{% bad %}",
                url: "",
              },
            ],
          },
          { status: 422 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await user.type(screen.getByLabelText("Text"), "bad template")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("text is not a valid Jinja2 template")
    })
    expect(screen.getByRole("alert").id).toBe("text-error")
  })
})
