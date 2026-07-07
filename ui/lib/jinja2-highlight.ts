import { RangeSetBuilder } from "@codemirror/state"
import { Decoration, type DecorationSet, EditorView, ViewPlugin, type ViewUpdate } from "@codemirror/view"

// Lightweight client-side feedback only — flags obviously unclosed/stray Jinja2
// delimiters as you type. It is not a Jinja2 parser and makes no claim of
// matching jinja2.Environment().parse() exactly; the server's 422 response
// stays the authoritative check (ADR: prompt text is Jinja2-syntax-validated
// on write, see docs/adr/0004-jinja2-text-is-validated-not-rendered.md).

const TAG_TOKEN_RE = /\{\{|\}\}|\{%|%\}|\{#|#\}/g

const CLOSER_FOR: Record<string, string> = { "{{": "}}", "{%": "%}", "{#": "#}" }
const OPENERS = new Set(Object.keys(CLOSER_FOR))
const CLOSERS = new Set(Object.values(CLOSER_FOR))

const validTag = Decoration.mark({ class: "cm-jinja2-tag" })
const unmatchedTag = Decoration.mark({ class: "cm-jinja2-tag-error" })

interface Token {
  text: string
  from: number
  to: number
}

function findTokens(text: string): Token[] {
  const tokens: Token[] = []
  TAG_TOKEN_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = TAG_TOKEN_RE.exec(text)) !== null) {
    tokens.push({ text: match[0], from: match.index, to: match.index + match[0].length })
  }
  return tokens
}

function computeDecorations(view: EditorView): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>()
  const marks: { from: number; to: number; ok: boolean }[] = []

  let pending: Token | null = null
  for (const token of findTokens(view.state.doc.toString())) {
    if (OPENERS.has(token.text)) {
      if (pending) marks.push({ from: pending.from, to: pending.to, ok: false })
      pending = token
    } else if (CLOSERS.has(token.text)) {
      if (pending && CLOSER_FOR[pending.text] === token.text) {
        marks.push({ from: pending.from, to: token.to, ok: true })
        pending = null
      } else {
        if (pending) marks.push({ from: pending.from, to: pending.to, ok: false })
        marks.push({ from: token.from, to: token.to, ok: false })
        pending = null
      }
    }
  }
  if (pending) marks.push({ from: pending.from, to: pending.to, ok: false })

  marks.sort((a, b) => a.from - b.from)
  for (const mark of marks) {
    builder.add(mark.from, mark.to, mark.ok ? validTag : unmatchedTag)
  }
  return builder.finish()
}

const jinja2Theme = EditorView.baseTheme({
  ".cm-jinja2-tag": {
    color: "#7c3aed",
    fontWeight: "600",
  },
  ".cm-jinja2-tag-error": {
    textDecoration: "underline wavy #dc2626",
  },
})

const jinja2DecorationPlugin = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet
    constructor(view: EditorView) {
      this.decorations = computeDecorations(view)
    }
    update(update: ViewUpdate) {
      if (update.docChanged) this.decorations = computeDecorations(update.view)
    }
  },
  { decorations: (plugin) => plugin.decorations }
)

/** Highlights {{ }}, {% %}, {# #} Jinja2 tags, flagging unmatched/unclosed ones. */
export function jinja2Highlight() {
  return [jinja2DecorationPlugin, jinja2Theme]
}
