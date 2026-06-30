import { render, screen, waitFor } from "@testing-library/react"
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

function renderForm() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
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

  it("shows success toast and clears form after successful create", async () => {
    const user = userEvent.setup()
    renderForm()

    await user.type(screen.getByLabelText("Slug"), "/my/prompt")
    await user.type(screen.getByLabelText("Text"), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    const { toast } = await import("sonner")
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Prompt created")
    })
    expect(screen.getByLabelText("Slug")).toHaveValue("")
    expect(screen.getByLabelText("Text")).toHaveValue("")
  })

  it("shows inline slug error on 409 conflict", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/create", () =>
        HttpResponse.json(
          {
            detail:
              "slug '/my/prompt' already has a live version; use POST /prompt/{id} to update it",
          },
          { status: 409 }
        )
      )
    )

    const user = userEvent.setup()
    renderForm()

    await user.type(screen.getByLabelText("Slug"), "/my/prompt")
    await user.type(screen.getByLabelText("Text"), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "already has a live version"
      )
    })
    // Error is associated with the slug input, not the text area
    expect(screen.getByRole("alert").id).toBe("slug-error")
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

    await user.type(screen.getByLabelText("Slug"), "/my/prompt")
    await user.type(screen.getByLabelText("Text"), "bad template")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "text is not a valid Jinja2 template"
      )
    })
    expect(screen.getByRole("alert").id).toBe("text-error")
  })

  it("shows inline slug error on 422 slug format failure", async () => {
    server.use(
      http.post("http://localhost:8000/prompt/create", () =>
        HttpResponse.json(
          {
            detail: [
              {
                type: "value_error",
                loc: ["body", "slug"],
                msg: "Value error, slug must look like a URL path: lowercase letters, digits and hyphens per segment",
                input: "bad_slug",
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

    await user.type(screen.getByLabelText("Slug"), "bad_slug")
    await user.type(screen.getByLabelText("Text"), "hello world")
    await user.click(screen.getByRole("button", { name: "Create prompt" }))

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "slug must look like a URL path"
      )
    })
    expect(screen.getByRole("alert").id).toBe("slug-error")
  })
})
