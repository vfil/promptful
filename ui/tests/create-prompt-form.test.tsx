import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { http, HttpResponse } from "msw"
import { server } from "./mocks/server"
import { CreatePromptForm } from "@/components/create-prompt-form"

vi.mock("sonner", () => ({
  toast: { success: vi.fn() },
  Toaster: () => null,
}))

const pushMock = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}))

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <CreatePromptForm />
    </QueryClientProvider>
  )
}

describe("CreatePromptForm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows success toast and redirects to the prompt list after successful create", async () => {
    const user = userEvent.setup()
    renderForm()

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
    renderForm()

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
    renderForm()

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
    renderForm()

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
    renderForm()

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
