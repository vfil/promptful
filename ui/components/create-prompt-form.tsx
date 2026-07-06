"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { CategoryCombobox } from "@/components/category-combobox"
import {
  ApiCallError,
  type ValidationError,
  createCategory,
  createPrompt,
  getCategories,
} from "@/lib/api"

interface FormErrors {
  leafSlugError?: string
  categoryError?: string
  textError?: string
  generic?: string
}

function classifyError(err: unknown): FormErrors {
  if (!(err instanceof ApiCallError)) return { generic: String(err) }
  const { status, detail } = err

  if (status === 409 && typeof detail === "string") {
    return { leafSlugError: detail }
  }

  if (status === 404 && typeof detail === "string") {
    return { categoryError: detail }
  }

  if (status === 422 && Array.isArray(detail)) {
    const errors = detail as ValidationError[]
    const leafSlugErr = errors.find((e) => e.loc[1] === "leaf_slug")
    const categoryErr = errors.find((e) => e.loc[1] === "category_id")
    const textErr = errors.find((e) => e.loc[1] === "text")
    return {
      leafSlugError: leafSlugErr?.msg.replace(/^Value error, /, ""),
      categoryError: categoryErr?.msg.replace(/^Value error, /, ""),
      textError: textErr?.msg.replace(/^Value error, /, ""),
    }
  }

  return { generic: typeof detail === "string" ? detail : "Request failed" }
}

export function CreatePromptForm() {
  const [leafSlug, setLeafSlug] = useState("")
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [parentCategoryId, setParentCategoryId] = useState<string | null>(null)
  const [text, setText] = useState("")
  const [errors, setErrors] = useState<FormErrors>({})

  const router = useRouter()
  const queryClient = useQueryClient()

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  })

  const mutation = useMutation({
    mutationFn: () => {
      if (!categoryId) throw new Error("Category is required")
      return createPrompt(leafSlug, categoryId, text)
    },
    onSuccess: () => {
      toast.success("Prompt created")
      queryClient.invalidateQueries({ queryKey: ["prompts"] })
      router.push("/")
    },
    onError: (err) => {
      setErrors(classifyError(err))
    },
  })

  async function handleCreateCategory(slug_segment: string) {
    const cat = await createCategory(slug_segment, parentCategoryId ?? undefined)
    // Write the new category into the cache immediately so the combobox renders it
    // before any background refetch completes.
    queryClient.setQueryData(["categories"], (old: typeof categories) => [...old, cat])
    setCategoryId(cat.id)
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setErrors({})
        mutation.mutate()
      }}
      className="flex flex-col gap-4 max-w-xl mx-auto mt-16 px-4"
    >
      <Link href="/" className="text-sm text-muted-foreground hover:underline">
        ← Back to prompts
      </Link>

      {/* Category row: Category picker + Parent category picker side by side */}
      <div className="flex gap-3">
        <div className="flex-1">
          <CategoryCombobox
            id="category"
            label="Category"
            value={categoryId}
            onChange={setCategoryId}
            categories={categories}
            onCreateCategory={handleCreateCategory}
            allowCreate
            placeholder="Select or create…"
          />
          {errors.categoryError && (
            <p id="category-error" role="alert" className="mt-1 text-sm text-destructive">
              {errors.categoryError}
            </p>
          )}
        </div>

        <div className="flex-1">
          <CategoryCombobox
            id="parent-category"
            label="Parent category"
            value={parentCategoryId}
            onChange={setParentCategoryId}
            categories={categories}
            placeholder="None (root)"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="leaf-slug" className="text-sm font-medium">
          Prompt name
        </label>
        <Input
          id="leaf-slug"
          value={leafSlug}
          onChange={(e) => setLeafSlug(e.target.value)}
          placeholder="first-lead"
          required
          aria-describedby={errors.leafSlugError ? "leaf-slug-error" : undefined}
        />
        {errors.leafSlugError && (
          <p id="leaf-slug-error" role="alert" className="text-sm text-destructive">
            {errors.leafSlugError}
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

      <Button type="submit" disabled={mutation.isPending || !categoryId}>
        {mutation.isPending ? "Creating…" : "Create prompt"}
      </Button>
    </form>
  )
}
