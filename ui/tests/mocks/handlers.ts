import { http, HttpResponse } from "msw"

const API_URL = "http://localhost:8000"

export const handlers = [
  http.post(`${API_URL}/prompt/create`, async ({ request }) => {
    const body = (await request.json()) as { slug: string; text: string }
    return HttpResponse.json(
      {
        id: "00000000-0000-0000-0000-000000000001",
        slug: body.slug,
        version: 1,
        text: body.text,
        is_deleted: false,
        created_at: "2024-01-01T00:00:00Z",
      },
      { status: 201 }
    )
  }),
]
