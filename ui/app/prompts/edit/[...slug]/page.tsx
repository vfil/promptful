"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { PromptForm } from "@/components/prompt-form"
import { getPromptBySlug } from "@/lib/api"

export default function EditPrompt() {
  const params = useParams<{ slug: string[] }>()
  const slug = "/" + (params.slug ?? []).join("/")

  const { data: prompt, isLoading, isError } = useQuery({
    queryKey: ["prompt", slug],
    queryFn: () => getPromptBySlug(slug),
    retry: false,
  })

  if (isLoading) {
    return <p className="mt-16 text-center text-sm text-muted-foreground">Loading…</p>
  }

  if (isError || !prompt) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <p className="text-sm text-muted-foreground">This prompt no longer exists.</p>
        <Link href="/" className="text-sm text-muted-foreground hover:underline">
          ← Back to prompts
        </Link>
      </div>
    )
  }

  return (
    // key={prompt.id}: a new Live Version always gets a new id, so this forces a
    // remount (fresh useState) whenever fresher data resolves — whether from our
    // own setQueryData on save, a background refetch replacing a stale cache hit,
    // or a concurrent editor's change (ADR-0003) landing while this page is open.
    <PromptForm
      key={prompt.id}
      mode="update"
      id={prompt.id}
      slug={prompt.slug}
      leafSlug={prompt.leaf_slug}
      categoryId={prompt.category_id}
      role={prompt.role}
      initialText={prompt.text}
    />
  )
}
