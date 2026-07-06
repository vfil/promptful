import { http, HttpResponse } from "msw"

const API_URL = "http://localhost:8000"

const CATEGORY: { id: string; slug_segment: string; parent_id: null; path: string; created_at: string } = {
  id: "cat-00000000-0000-0000-0000-000000000001",
  slug_segment: "sales",
  parent_id: null,
  path: "/sales",
  created_at: "2024-01-01T00:00:00Z",
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
]
