"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { CategoryCombobox } from "@/components/category-combobox"
import { PromptTextEditor } from "@/components/prompt-text-editor"
import { PromptGuidancePanel } from "@/components/prompt-guidance-panel"
import {
  ApiCallError,
  type PromptRole,
  type ValidationError,
  createCategory,
  createPrompt,
  getCategories,
  getPromptBySlug,
  updatePrompt,
} from "@/lib/api"

interface PromptFormProps {
  mode: "create" | "update"
  /** Update mode only: the current Live Version's id, used as the optimistic-concurrency token. */
  id?: string
  /** Update mode only: the prompt's full slug, used to re-resolve the Live Version on conflict. */
  slug?: string
  leafSlug?: string
  categoryId?: string
  role?: PromptRole
  initialText?: string
}

interface FormErrors {
  leafSlugError?: string
  categoryError?: string
  textError?: string
  conflict?: boolean
  generic?: string
}

function classifyError(err: unknown, mode: "create" | "update"): FormErrors {
  if (!(err instanceof ApiCallError)) return { generic: String(err) }
  const { status, detail } = err

  if (mode === "create" && status === 409 && typeof detail === "string") {
    return { leafSlugError: detail }
  }

  if (mode === "update" && status === 409) {
    return { conflict: true }
  }

  if (mode === "create" && status === 404 && typeof detail === "string") {
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

export function PromptForm(props: PromptFormProps) {
  const isUpdate = props.mode === "update"

  const [leafSlug, setLeafSlug] = useState(props.leafSlug ?? "")
  const [categoryId, setCategoryId] = useState<string | null>(props.categoryId ?? null)
  const [parentCategoryId, setParentCategoryId] = useState<string | null>(null)
  const [role, setRole] = useState<PromptRole | "">(props.role ?? "")
  const [text, setText] = useState(props.initialText ?? "")
  const [liveId, setLiveId] = useState(props.id)
  const [errors, setErrors] = useState<FormErrors>({})

  const router = useRouter()
  const queryClient = useQueryClient()

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  })

  // Update mode: the "Parent category" box is purely informational (mirrors the
  // create-form layout) — derive it from the fixed Category rather than tracking it.
  const derivedParentCategoryId = isUpdate
    ? categories.find((c) => c.id === categoryId)?.parent_id ?? null
    : parentCategoryId

  const mutation = useMutation({
    mutationFn: () => {
      if (props.mode === "create") {
        if (!categoryId) throw new Error("Category is required")
        if (!role) throw new Error("Role is required")
        return createPrompt(leafSlug, categoryId, role, text)
      }
      return updatePrompt(liveId!, text)
    },
    onSuccess: (updated) => {
      toast.success(isUpdate ? "Prompt updated" : "Prompt created")
      // Seed the per-slug cache immediately so a subsequent visit to the edit page
      // (e.g. clicking "Edit" again from the list) doesn't serve pre-mutation text
      // out of a stale cache entry — see ADR-0006.
      queryClient.setQueryData(["prompt", updated.slug], updated)
      queryClient.invalidateQueries({ queryKey: ["prompts"] })
      router.push("/")
    },
    onError: (err) => {
      setErrors(classifyError(err, props.mode))
    },
  })

  async function handleCreateCategory(slug_segment: string) {
    const cat = await createCategory(slug_segment, parentCategoryId ?? undefined)
    // Write the new category into the cache immediately so the combobox renders it
    // before any background refetch completes.
    queryClient.setQueryData(["categories"], (old: typeof categories) => [...old, cat])
    setCategoryId(cat.id)
  }

  async function handleReloadLatest() {
    if (!props.slug) return
    const latest = await getPromptBySlug(props.slug)
    setLiveId(latest.id)
    setText(latest.text)
    setErrors({})
  }

  return (
    <div className="mx-auto mt-16 flex max-w-4xl items-start gap-6 px-4">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          setErrors({})
          if (!text.trim()) {
            setErrors({ textError: "Text is required" })
            return
          }
          mutation.mutate()
        }}
        className="flex flex-1 flex-col gap-4"
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
              onChange={isUpdate ? () => {} : setCategoryId}
              categories={categories}
              onCreateCategory={isUpdate ? undefined : handleCreateCategory}
              allowCreate={!isUpdate}
              disabled={isUpdate}
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
              value={derivedParentCategoryId}
              onChange={isUpdate ? () => {} : setParentCategoryId}
              categories={categories}
              disabled={isUpdate}
              placeholder="None (root)"
            />
          </div>
        </div>

        <div className="flex gap-3">
          <div className="flex-1">
            <label htmlFor="leaf-slug" className="text-sm font-medium">
              Prompt name
            </label>
            <Input
              id="leaf-slug"
              value={leafSlug}
              onChange={(e) => setLeafSlug(e.target.value)}
              placeholder="first-lead"
              required
              disabled={isUpdate}
              aria-describedby={errors.leafSlugError ? "leaf-slug-error" : undefined}
            />
            {errors.leafSlugError && (
              <p id="leaf-slug-error" role="alert" className="text-sm text-destructive">
                {errors.leafSlugError}
              </p>
            )}
          </div>

          <div className="flex-1">
            <label htmlFor="role" className="text-sm font-medium">
              Role
            </label>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value as PromptRole)}
              required
              disabled={isUpdate}
              className="h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs outline-none transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm dark:bg-input/30"
            >
              <option value="" disabled>
                Select a role…
              </option>
              <option value="system">System</option>
              <option value="user">User</option>
              <option value="assistant">Assistant</option>
            </select>
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="text" className="text-sm font-medium">
            Text
          </label>
          <PromptTextEditor
            value={text}
            onChange={setText}
            placeholder="Your prompt text — Jinja2 templates supported (e.g. {{ variable }})"
            ariaLabel="Text"
            ariaDescribedBy={errors.textError ? "text-error" : undefined}
            ariaInvalid={!!errors.textError}
          />
          {errors.textError && (
            <p id="text-error" role="alert" className="text-sm text-destructive">
              {errors.textError}
            </p>
          )}
        </div>

        {errors.conflict && (
          <div
            role="alert"
            className="flex flex-col gap-2 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <p>This prompt changed elsewhere. Reload to see the latest version before saving.</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleReloadLatest}
              className="self-start"
            >
              Reload latest version
            </Button>
          </div>
        )}

        {errors.generic && (
          <p role="alert" className="text-sm text-destructive">
            {errors.generic}
          </p>
        )}

        <Button
          type="submit"
          disabled={mutation.isPending || (!isUpdate && (!categoryId || !role))}
        >
          {mutation.isPending
            ? isUpdate
              ? "Saving…"
              : "Creating…"
            : isUpdate
              ? "Save changes"
              : "Create prompt"}
        </Button>
      </form>

      <PromptGuidancePanel role={role || null} />
    </div>
  )
}
