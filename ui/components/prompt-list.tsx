"use client"

import Link from "next/link"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { ApiCallError, type PromptSummary, deletePrompt, listPrompts } from "@/lib/api"

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function DeletePromptAction({ prompt }: { prompt: PromptSummary }) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => deletePrompt(prompt.id),
    onSuccess: () => {
      toast.success("Prompt deleted")
      queryClient.invalidateQueries({ queryKey: ["prompts"] })
    },
    onError: (err) => {
      // A stale row (its Live Version changed or was deleted elsewhere since
      // the list was fetched) 409s — refetch so the row reflects reality
      // instead of silently retrying (ADR-0003, ADR-0008).
      if (err instanceof ApiCallError && err.status === 409) {
        toast.error("This prompt changed elsewhere — refreshing the list")
      } else {
        toast.error("Failed to delete prompt")
      }
      queryClient.invalidateQueries({ queryKey: ["prompts"] })
    },
  })

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
          Delete
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this prompt?</AlertDialogTitle>
          <AlertDialogDescription>
            <span className="font-mono">{prompt.slug}</span> will no longer be readable at this
            slug. Its version history is kept, and re-creating the same slug later continues that
            history.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:bg-destructive/60"
            disabled={mutation.isPending}
            onClick={(e) => {
              e.preventDefault()
              mutation.mutate()
            }}
          >
            {mutation.isPending ? "Deleting…" : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
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
                  <div className="flex justify-end gap-1">
                    <Button asChild variant="ghost" size="sm">
                      <Link href={`/prompts/edit${prompt.slug}`}>Edit</Link>
                    </Button>
                    <DeletePromptAction prompt={prompt} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
