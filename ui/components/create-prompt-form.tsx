"use client"

import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface PromptVersion {
  id: string
  slug: string
  version: number
  text: string
  is_deleted: boolean
  created_at: string
}

interface ValidationError {
  loc: string[]
  msg: string
  type: string
}

class ApiCallError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string | ValidationError[]
  ) {
    super("API call failed")
    this.name = "ApiCallError"
  }
}

interface FormErrors {
  slugError?: string
  textError?: string
  generic?: string
}

async function createPrompt(slug: string, text: string): Promise<PromptVersion> {
  const res = await fetch(`${API_URL}/prompt/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug, text }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiCallError(res.status, body.detail ?? "Request failed")
  }
  return res.json()
}

function classifyError(err: unknown): FormErrors {
  if (!(err instanceof ApiCallError)) return { generic: String(err) }
  const { status, detail } = err

  if (status === 409 && typeof detail === "string") {
    return { slugError: detail }
  }

  if (status === 422 && Array.isArray(detail)) {
    const slugErr = detail.find((e) => e.loc[1] === "slug")
    const textErr = detail.find((e) => e.loc[1] === "text")
    return {
      slugError: slugErr?.msg.replace(/^Value error, /, ""),
      textError: textErr?.msg.replace(/^Value error, /, ""),
    }
  }

  return { generic: typeof detail === "string" ? detail : "Request failed" }
}

export function CreatePromptForm() {
  const [slug, setSlug] = useState("")
  const [text, setText] = useState("")
  const [errors, setErrors] = useState<FormErrors>({})

  const mutation = useMutation<PromptVersion, ApiCallError>({
    mutationFn: () => createPrompt(slug, text),
    onSuccess: () => {
      toast.success("Prompt created")
      setSlug("")
      setText("")
      setErrors({})
    },
    onError: (err) => {
      setErrors(classifyError(err))
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setErrors({})
        mutation.mutate()
      }}
      className="flex flex-col gap-4 max-w-xl mx-auto mt-16 px-4"
    >
      <div className="flex flex-col gap-1">
        <label htmlFor="slug" className="text-sm font-medium">
          Slug
        </label>
        <Input
          id="slug"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          placeholder="/sales/screening/first-lead"
          required
          aria-describedby={errors.slugError ? "slug-error" : undefined}
        />
        {errors.slugError && (
          <p id="slug-error" role="alert" className="text-sm text-destructive">
            {errors.slugError}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="text" className="text-sm font-medium">
          Text
        </label>
        <Textarea
          id="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Your prompt text — Jinja2 templates supported (e.g. {{ variable }})"
          required
          rows={8}
          aria-describedby={errors.textError ? "text-error" : undefined}
        />
        {errors.textError && (
          <p id="text-error" role="alert" className="text-sm text-destructive">
            {errors.textError}
          </p>
        )}
      </div>

      {errors.generic && (
        <p role="alert" className="text-sm text-destructive">
          {errors.generic}
        </p>
      )}

      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending ? "Creating…" : "Create prompt"}
      </Button>
    </form>
  )
}
