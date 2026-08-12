"use client"

import { useMemo, useState } from "react"
import CodeMirror from "@uiw/react-codemirror"
import { markdown } from "@codemirror/lang-markdown"
import { EditorView } from "@codemirror/view"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { jinja2Highlight } from "@/lib/jinja2-highlight"
import { cn } from "@/lib/utils"

interface PromptTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  ariaLabel: string
  ariaDescribedBy?: string
  ariaInvalid?: boolean
}

// Preview intentionally never executes Jinja2 — `{{ }}`/`{% %}` render as
// literal text via react-markdown, matching the API's own rendering boundary
// (docs/adr/0004-jinja2-text-is-validated-not-rendered.md).
export function PromptTextEditor({
  value,
  onChange,
  placeholder,
  ariaLabel,
  ariaDescribedBy,
  ariaInvalid,
}: PromptTextEditorProps) {
  const [mode, setMode] = useState<"edit" | "preview">("edit")

  const extensions = useMemo(
    () => [
      markdown(),
      jinja2Highlight(),
      EditorView.lineWrapping,
      EditorView.contentAttributes.of({
        role: "textbox",
        "aria-multiline": "true",
        "aria-label": ariaLabel,
        ...(ariaDescribedBy ? { "aria-describedby": ariaDescribedBy } : {}),
        ...(ariaInvalid ? { "aria-invalid": "true" } : {}),
      }),
    ],
    [ariaLabel, ariaDescribedBy, ariaInvalid]
  )

  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-1 self-start rounded-md border p-0.5">
        <Button
          type="button"
          size="xs"
          variant={mode === "edit" ? "secondary" : "ghost"}
          onClick={() => setMode("edit")}
        >
          Edit
        </Button>
        <Button
          type="button"
          size="xs"
          variant={mode === "preview" ? "secondary" : "ghost"}
          onClick={() => setMode("preview")}
        >
          Preview
        </Button>
      </div>

      {mode === "edit" ? (
        <CodeMirror
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          extensions={extensions}
          basicSetup={{ lineNumbers: false, foldGutter: false }}
          className="overflow-hidden rounded-md border text-sm"
        />
      ) : (
        <div
          className={cn(
            "min-h-32 rounded-md border px-3 py-2 text-sm",
            "[&_h1]:mt-2 [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:mt-2 [&_h2]:text-base [&_h2]:font-semibold",
            "[&_p]:mb-2 [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5",
            "[&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs",
            "[&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-2"
          )}
        >
          <ReactMarkdown>{value || "*Nothing to preview yet.*"}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}
