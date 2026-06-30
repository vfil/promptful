# ui

Next.js (App Router) frontend for Promptful.

## Setup

```bash
pnpm install
```

Create a `.env.local` file with the API base URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

```bash
pnpm dev
```

Runs `tsc --noEmit --watch` and `next dev` concurrently. TypeScript errors appear in the terminal
even if the Next.js dev server compiles successfully — a red squiggly in the `tsc` output is a real
type error.

Requires the backend running with CORS enabled for `localhost:3000`. See `api/README.md` for
backend startup.

## Type-check only

```bash
pnpm typecheck
```

## Tests

```bash
pnpm test          # watch mode
pnpm test --run    # single pass (CI)
```

Tests use [Vitest](https://vitest.dev/) + [@testing-library/react](https://testing-library.com/)
+ [MSW](https://mswjs.io/) for request mocking. No running server needed.

## Build

```bash
pnpm build
pnpm start
```
