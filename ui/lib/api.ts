const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface Category {
  id: string
  slug_segment: string
  parent_id: string | null
  path: string
  created_at: string
}

export interface PromptVersion {
  id: string
  slug: string
  leaf_slug: string
  category_id: string
  version: number
  text: string
  is_deleted: boolean
  created_at: string
}

export interface PromptSummary {
  id: string
  slug: string
  leaf_slug: string
  category_id: string
  version: number
  created_at: string
}

export interface ValidationError {
  loc: string[]
  msg: string
  type: string
}

export class ApiCallError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string | ValidationError[]
  ) {
    super("API call failed")
    this.name = "ApiCallError"
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiCallError(res.status, body.detail ?? "Request failed")
  }
  return res.json()
}

export async function getCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/categories")
}

export async function createCategory(
  slug_segment: string,
  parent_id?: string
): Promise<Category> {
  return apiFetch<Category>("/categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug_segment, ...(parent_id ? { parent_id } : {}) }),
  })
}

export async function listPrompts(): Promise<PromptSummary[]> {
  return apiFetch<PromptSummary[]>("/prompts")
}

export async function createPrompt(
  leaf_slug: string,
  category_id: string,
  text: string
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>("/prompt/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ leaf_slug, category_id, text }),
  })
}

export async function getPromptBySlug(slug: string): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(`/prompt?slug=${encodeURIComponent(slug)}`)
}

export async function updatePrompt(id: string, text: string): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(`/prompt/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  })
}
