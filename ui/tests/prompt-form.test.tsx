import { render, screen, waitFor, within } from "@testing-library/react"
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

// The Text field is a CodeMirror editor (contenteditable), not a native
// textarea — it exposes an accessible name via aria-label rather than
// label[for], and has no .value, so assertions use toHaveTextContent.
function textEditor() {
  return screen.getByRole("textbox", { name: "Text" })
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
    await user.selectOptions(screen.getByLabelText("Role"), "user")
    await user.type(textEditor(), "hello world")
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
    await user.selectOptions(screen.getByLabelText("Role"), "user")
    await user.type(textEditor(), "hello world")
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
    await user.selectOptions(screen.getByLabelText("Role"), "user")
    await user.type(textEditor(), "bad template")
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
    await user.selectOptions(screen.getByLabelText("Role"), "user")
    await user.type(textEditor(), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "leaf_slug must be lowercase letters"
      )
    })
    expect(screen.getByRole("alert").id).toBe("leaf-slug-error")
  })

  it("disables Create prompt until both Category and Role are chosen", async () => {
    const user = userEvent.setup()
    renderForm(<PromptForm mode="create" />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    expect(screen.getByRole("button", { name: "Create prompt" })).toBeDisabled()

    await user.click(screen.getByRole("combobox", { name: "Category" }))
    await user.click(await screen.findByText("/sales"))
    expect(screen.getByRole("button", { name: "Create prompt" })).toBeDisabled()

    await user.selectOptions(screen.getByLabelText("Role"), "system")
    expect(screen.getByRole("button", { name: "Create prompt" })).toBeEnabled()
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
  role: "user" as const,
  initialText: "hello world",
}

describe("PromptForm (update mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("pre-fills text and disables Category/Parent category/Prompt name/Role", async () => {
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await waitFor(() => screen.getByRole("combobox", { name: "Category" }))
    expect(screen.getByRole("combobox", { name: "Category" })).toBeDisabled()
    expect(screen.getByRole("combobox", { name: "Parent category" })).toBeDisabled()
    expect(screen.getByLabelText("Prompt name")).toBeDisabled()
    expect(screen.getByLabelText("Role")).toBeDisabled()
    expect(screen.getByLabelText("Role")).toHaveValue("user")
    expect(textEditor()).toHaveTextContent("hello world")
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument()
  })

  it("shows success toast and redirects to the prompt list after successful update", async () => {
    const user = userEvent.setup()
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await user.clear(textEditor())
    await user.type(textEditor(), "updated text")
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

    await user.type(textEditor(), " more")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("changed elsewhere")
    })

    // The default GET /prompt?slug=... handler returns the Live Version's text.
    await user.click(screen.getByRole("button", { name: "Reload latest version" }))

    await waitFor(() => {
      expect(textEditor()).toHaveTextContent("hello world")
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

    await user.type(textEditor(), "bad template")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("text is not a valid Jinja2 template")
    })
    expect(screen.getByRole("alert").id).toBe("text-error")
  })

  it("deletes the prompt via the confirm dialog and redirects to the prompt list", async () => {
    const user = userEvent.setup()
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await user.click(screen.getByRole("button", { name: "Delete prompt" }))
    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Delete" }))

    const { toast } = await import("sonner")
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Prompt deleted")
    })
    expect(pushMock).toHaveBeenCalledWith("/")
  })

  it("shows the conflict banner instead of deleting when the version is stale (409)", async () => {
    server.use(
      http.delete("http://localhost:8000/prompt/:id", () =>
        HttpResponse.json(
          { detail: "this version is no longer the current version; re-read it and retry" },
          { status: 409 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm(<PromptForm {...UPDATE_PROPS} />)

    await user.click(screen.getByRole("button", { name: "Delete prompt" }))
    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Delete" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("changed elsewhere")
    })
    expect(pushMock).not.toHaveBeenCalledWith("/")
  })
})
