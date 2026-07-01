# Add Categories

Replace the freeform Slug input with a first-class Category entity. Users pick or create a
Category via a combobox on the Create Prompt page; the Slug is derived automatically from the
Category hierarchy and the Prompt's Leaf Slug.

See also: [ADR-0005](../../docs/adr/0005-categories-with-materialized-path.md)

---

## Domain model changes

| Term | Definition |
|---|---|
| **Category** | A named grouping with one Slug Segment and an optional parent Category. |
| **Slug Segment** | The slug-safe name of a Category (e.g. `screening`). Immutable. |
| **Category Path** | The materialized full path of a Category (e.g. `/sales/screening`). |
| **Leaf Slug** | The Prompt's local slug-safe name within its Category (e.g. `first-lead`). |
| **Slug** | `Category Path + "/" + Leaf Slug` — the full, stable Prompt address. |

Full language is in [CONTEXT.md](../../CONTEXT.md).

---

## Constraints

- A Category's Slug Segment is **immutable** — no rename operation.
- A Category **cannot be deleted** if it has child Categories or live Prompts (409).
- A Prompt's `category_id` is **fixed at creation** — no re-assignment.
- Sibling Categories must have unique Slug Segments: `UNIQUE(slug_segment, parent_id) NULLS NOT DISTINCT`.
- Within a Category, Prompts must have unique Leaf Slugs (per version): `UNIQUE(leaf_slug, category_id, version)`.

---

## Step-by-step implementation plan

### Step 1 — Database: `categories` table

Create an Alembic migration that adds the `categories` table:

```sql
CREATE TABLE categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug_segment VARCHAR NOT NULL
        CHECK (slug_segment ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    parent_id   UUID REFERENCES categories(id),
    path        VARCHAR NOT NULL,           -- e.g. /sales/screening
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ON categories (slug_segment, parent_id) NULLS NOT DISTINCT;
```

`path` is computed by the application at creation time as:
- Root category: `"/" + slug_segment`
- Child category: `parent.path + "/" + slug_segment`

### Step 2 — Database: update `prompts` table

Same migration (or a follow-up migration) changes the `prompts` table:

- Add `leaf_slug VARCHAR NOT NULL CHECK (leaf_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')`
- Add `category_id UUID NOT NULL REFERENCES categories(id)`
- Drop `slug` column
- Drop `UNIQUE(slug, version)` constraint
- Add `UNIQUE(leaf_slug, category_id, version)`

> No data migration is required — the project has no production data yet.

### Step 3 — Backend: Category ORM model

New file `api/app/models/category.py`:

```python
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID]
    slug_segment: Mapped[str]
    parent_id: Mapped[uuid.UUID | None]   # nullable FK to self
    path: Mapped[str]                      # materialized e.g. /sales/screening
    created_at: Mapped[datetime]
```

### Step 4 — Backend: Category schemas

New file `api/app/schemas/category.py`:

```python
class CategoryCreate(BaseModel):
    slug_segment: str       # validated against slug-segment regex
    parent_id: uuid.UUID | None = None

class CategoryRead(BaseModel):
    id: uuid.UUID
    slug_segment: str
    parent_id: uuid.UUID | None
    path: str
    created_at: datetime
```

### Step 5 — Backend: Category router

New file `api/app/routers/category.py` with two endpoints:

**GET /categories**
- Returns a flat list of all `CategoryRead` objects.
- No filtering — the client populates the combobox from the full list.

**POST /categories**
- Body: `CategoryCreate`
- Validates `slug_segment` format (422 on failure).
- If `parent_id` is provided, fetches the parent; 404 if not found.
- Computes `path`:
  - Root: `"/" + slug_segment`
  - Child: `parent.path + "/" + slug_segment`
- Inserts row; returns 201 with `CategoryRead`.
- 409 on `UNIQUE` violation (duplicate sibling slug_segment).

Register the router in `api/app/main.py`.

### Step 6 — Backend: update Prompt model and schemas

Update `api/app/models/prompt.py`:
- Replace `slug: Mapped[str]` with `leaf_slug: Mapped[str]` and `category_id: Mapped[uuid.UUID]`.

Update `api/app/schemas/prompt.py`:
- `PromptCreate`: replace `slug` field with `leaf_slug` + `category_id`.
- `PromptVersionRead`: keep a computed `slug` field (populated by joining to Category at query time as `category.path + "/" + leaf_slug`); add `category_id` and `leaf_slug` fields.

### Step 7 — Backend: update Prompt router

Update `api/app/routers/prompt.py`:

- **POST /prompt/create**: accept `leaf_slug + category_id` instead of `slug`. Validate that the category exists (404 if not). Conflict check: 409 if there is already a Live Version for `(leaf_slug, category_id)`. Derive and return `slug` in the response.
- **GET /prompt** (by slug): resolve the incoming `slug` query param by splitting on the last `/` into `(category_path, leaf_slug)`, look up the Category by `path`, then query `(leaf_slug, category_id)`. Everything else unchanged.
- **POST /prompt/{id}** and **DELETE /prompt/{id}**: no changes — these operate by Version `id`.
- **GET /prompt/{id}**: join to Category to populate `slug` in the response.

### Step 8 — Backend: tests

Update `api/tests/test_prompt_routes.py`:
- Replace all `slug` payloads with `leaf_slug + category_id`.
- Add a Category creation step in relevant fixtures.

Add `api/tests/test_category_routes.py`:
- Create root category: 201 with correct `path`.
- Create child category: 201 with parent's `path` + segment.
- Duplicate sibling: 409.
- Invalid slug_segment: 422.
- Unknown parent_id: 404.
- GET /categories returns flat list.

### Step 9 — Frontend: Category API client

Add a `getCategories` function and a `createCategory` function to the API client (alongside the existing `createPrompt`):

```ts
interface Category {
  id: string
  slug_segment: string
  parent_id: string | null
  path: string
  created_at: string
}

async function getCategories(): Promise<Category[]>
async function createCategory(slug_segment: string, parent_id?: string): Promise<Category>
```

### Step 10 — Frontend: Category combobox component

Create `ui/components/category-combobox.tsx` using the shadcn combobox pattern (Command + Popover):
- Fetches categories via `useQuery` from `GET /categories`.
- Displays each option as its full `path` (e.g. `/sales/screening`).
- Search filters by `path` substring.
- "Create `<typed-value>`" option appears when no exact match is found — calls `createCategory` inline and selects the new entry.
- Accepts a `value` (selected category id) and `onChange` callback.

### Step 11 — Frontend: update Create Prompt form

Update `ui/components/create-prompt-form.tsx`:

- **Remove** the `slug` text input.
- **Add** a `leaf_slug` text input (label: "Prompt name", placeholder: `first-lead`).
- **Add** two side-by-side `CategoryCombobox` fields:
  - "Category" — the Category this Prompt will belong to (required).
  - "Parent category" — when the user intends to create a new Category inline, this optionally sets its parent (not required, always visible).
- Pass `category_id` (from "Category" combobox) and `leaf_slug` to the `createPrompt` mutation.
- The "Parent category" value is only consumed when `createCategory` is called from within the "Category" combobox.
- Update error classification: 409 on `(leaf_slug, category_id)` conflict maps to the leaf_slug field; category 404 maps to the Category combobox.

### Step 12 — Frontend: tests

Update `ui/tests/create-prompt-form.test.tsx`:
- Replace slug input interactions with leaf_slug input + Category combobox interactions.
- Add MSW handlers for `GET /categories` and `POST /categories`.
- Test: select existing category → prompt created.
- Test: type new category name → category created inline → prompt created.
- Test: 409 conflict → error shown near leaf_slug field.

---

## API surface summary

### New endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/categories` | Flat list of all categories |
| POST | `/categories` | Create a category |

### Changed endpoints

| Method | Path | What changed |
|---|---|---|
| POST | `/prompt/create` | Body: `leaf_slug + category_id` instead of `slug` |
| GET | `/prompt` | `?slug=` still works; resolved via category path lookup |
| GET | `/prompt/{id}` | Response includes computed `slug`, `leaf_slug`, `category_id` |

---

## Out of scope

- Category rename / move
- Prompt re-assignment to a different Category
- Category delete (requires its own management UI)
- Ownership / visibility scoping (deferred per CONTEXT.md domain model)
