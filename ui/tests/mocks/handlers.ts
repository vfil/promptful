import { http, HttpResponse } from "msw"

const API_URL = "http://localhost:8000"

const CATEGORY: { id: string; slug_segment: string; parent_id: null; path: string; created_at: string } = {
  id: "cat-00000000-0000-0000-0000-000000000001",
  slug_segment: "sales",
  parent_id: null,
  path: "/sales",
  created_at: "2024-01-01T00:00:00Z",
}

interface PromptRecord {
  id: string
  slug: string
  leaf_slug: string
  category_id: string
  version: number
  text: string
  is_deleted: boolean
  created_at: string
}

function versionId(version: number): string {
  return `00000000-0000-0000-0000-${String(version).padStart(12, "0")}`
}

const INITIAL_PROMPT: PromptRecord = {
  id: versionId(1),
  slug: "/sales/my-prompt",
  leaf_slug: "my-prompt",
  category_id: CATEGORY.id,
  version: 1,
  text: "hello world",
  is_deleted: false,
  created_at: "2024-01-01T00:00:00Z",
}

// A tiny in-memory "backend" for /sales/my-prompt so tests can exercise a real
// fetch-by-slug -> update -> fetch-by-slug-again cycle, the same cache path a real
// Edit -> save -> Edit revisit takes. Reset between tests via resetPromptStore().
let promptStore = new Map<string, PromptRecord>([[INITIAL_PROMPT.slug, { ...INITIAL_PROMPT }]])

export function resetPromptStore(): void {
  promptStore = new Map([[INITIAL_PROMPT.slug, { ...INITIAL_PROMPT }]])
}

export const handlers = [
  http.get(`${API_URL}/categories`, () => {
    return HttpResponse.json([CATEGORY])
  }),

  http.get(`${API_URL}/prompts`, () => {
    return HttpResponse.json([])
  }),

  http.post(`${API_URL}/categories`, async ({ request }) => {
    const body = (await request.json()) as { slug_segment: string; parent_id?: string }
    return HttpResponse.json(
      {
        id: "cat-00000000-0000-0000-0000-000000000002",
        slug_segment: body.slug_segment,
        parent_id: body.parent_id ?? null,
        path: `/${body.slug_segment}`,
        created_at: "2024-01-01T00:00:00Z",
      },
      { status: 201 }
    )
  }),

  http.post(`${API_URL}/prompt/create`, async ({ request }) => {
    const body = (await request.json()) as {
      leaf_slug: string
      category_id: string
      text: string
    }
    return HttpResponse.json(
      {
        id: "00000000-0000-0000-0000-000000000001",
        slug: `/sales/${body.leaf_slug}`,
        leaf_slug: body.leaf_slug,
        category_id: body.category_id,
        version: 1,
        text: body.text,
        is_deleted: false,
        created_at: "2024-01-01T00:00:00Z",
      },
      { status: 201 }
    )
  }),

  http.get(`${API_URL}/prompt`, ({ request }) => {
    const slug = new URL(request.url).searchParams.get("slug")
    const record = slug ? promptStore.get(slug) : undefined
    if (record) {
      return HttpResponse.json(record)
    }
    return HttpResponse.json({ detail: "slug has no live version" }, { status: 404 })
  }),

  http.post(`${API_URL}/prompt/:id`, async ({ request, params }) => {
    const body = (await request.json()) as { text: string }
    const entry = [...promptStore.entries()].find(([, r]) => r.id === params.id)
    if (!entry) {
      return HttpResponse.json({ detail: "no prompt version with that id" }, { status: 404 })
    }
    const [slug, current] = entry
    const updated: PromptRecord = {
      ...current,
      id: versionId(current.version + 1),
      version: current.version + 1,
      text: body.text,
    }
    promptStore.set(slug, updated)
    return HttpResponse.json(updated)
  }),
]
