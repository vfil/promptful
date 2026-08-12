"use client"

import { useState } from "react"
import { CheckIcon, CopyIcon, PanelRightCloseIcon, PanelRightOpenIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PROMPT_TEMPLATES } from "@/lib/prompt-templates"
import type { PromptRole } from "@/lib/api"

interface PromptGuidancePanelProps {
  role: PromptRole | null
}

export function PromptGuidancePanel({ role }: PromptGuidancePanelProps) {
  const [open, setOpen] = useState(true)

  if (!open) {
    return (
      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={() => setOpen(true)}
        aria-label="Show writing guide"
        className="shrink-0"
      >
        <PanelRightOpenIcon />
      </Button>
    )
  }

  const template = role ? PROMPT_TEMPLATES[role] : null

  return (
    <aside className="flex w-72 shrink-0 flex-col gap-3 rounded-md border p-4 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="font-medium">{template ? template.title : "Writing guide"}</h2>
          {template && <p className="mt-1 text-xs text-muted-foreground">{template.summary}</p>}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={() => setOpen(false)}
          aria-label="Hide writing guide"
        >
          <PanelRightCloseIcon className="h-4 w-4" />
        </Button>
      </div>

      {!template ? (
        <p className="text-xs text-muted-foreground">
          Select a role above to see a template for writing this prompt.
        </p>
      ) : (
        <div className="flex flex-col gap-4 overflow-y-auto">
          {template.sections.map((section) => (
            <TemplateSection key={section.heading} {...section} />
          ))}
        </div>
      )}
    </aside>
  )
}

function TemplateSection({
  heading,
  guidance,
  example,
}: {
  heading: string
  guidance: string
  example: string
}) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(example)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard access can be denied/unavailable — copy is a convenience, not critical.
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {heading}
        </h3>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={`Copy ${heading} example`}
          className="text-muted-foreground hover:text-foreground"
        >
          {copied ? <CheckIcon className="h-3.5 w-3.5" /> : <CopyIcon className="h-3.5 w-3.5" />}
        </button>
      </div>
      <p className="text-xs text-muted-foreground">{guidance}</p>
      <pre className="overflow-x-auto rounded-md bg-muted p-2 text-xs whitespace-pre-wrap">
        {example}
      </pre>
    </div>
  )
}
