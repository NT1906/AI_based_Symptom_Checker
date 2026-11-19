# UI primitives (shadcn/ui)

**Owner:** Nisarg · **Task:** S2-NIS-19 (#320)

Vendored [shadcn/ui](https://ui.shadcn.com) components (MIT), generated with
`npx shadcn@4.23.0 add <name>` using the `radix-nova` style (`components.json`).

- Import from `@/components/ui/<name>`; compose classes with `cn` from `@/lib/utils`.
- Keep these generic: no app logic, API calls or medical wording here.
- Colours come from the tokens in `src/index.css` (`bg-primary`, `text-muted-foreground`,
  `bg-danger` …), so light and dark mode work automatically.
- This app runs **React 18**: shadcn v4 targets React 19, so any primitive that Radix
  wraps with `asChild` or that needs a ref (Button, Input, Textarea) uses `forwardRef`.
  Do the same when adding such a component.
- After `shadcn add`, check that the generated file imports `cn` from `@/lib/utils`
  (not the `cn` package) and add the `@file` header CI requires.

Test: `npm test` (components are covered through the features that use them).
