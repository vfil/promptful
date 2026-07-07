"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { listPrompts } from "@/lib/api"

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

export function PromptList() {
  const { data: prompts = [], isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: listPrompts,
  })

  return (
    <div className="flex flex-col gap-4 max-w-2xl mx-auto mt-16 px-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-medium">Prompts</h1>
        <Button asChild>
          <Link href="/prompts/new">New prompt</Link>
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : prompts.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <p className="text-sm text-muted-foreground">No prompts yet</p>
          <Button asChild>
            <Link href="/prompts/new">New prompt</Link>
          </Button>
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-2 font-medium">Slug</th>
              <th className="py-2 font-medium">Created</th>
              <th className="py-2 font-medium sr-only">Actions</th>
            </tr>
          </thead>
          <tbody>
            {prompts.map((prompt) => (
              <tr key={prompt.id} className="border-b last:border-0">
                <td className="py-2 font-mono">{prompt.slug}</td>
                <td className="py-2 text-muted-foreground">{formatDate(prompt.created_at)}</td>
                <td className="py-2 text-right">
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/prompts/edit${prompt.slug}`}>Edit</Link>
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
