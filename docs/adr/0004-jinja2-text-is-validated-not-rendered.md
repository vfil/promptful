# Prompt text is Jinja2-syntax-validated on write; rendering is out of scope here

`text` is stored as plain `TEXT` and is expected to contain Jinja2 template syntax, but this
endpoint never executes it. Create and Update parse the text with Jinja2's parser
(`Environment().parse(text)`, no execution) and reject malformed templates with 422 before they
reach the database. Reads (`GET`) always return the raw, unrendered text.

Actual rendering (executing a template against caller-supplied variables) was deliberately left
out of this endpoint. It's a distinct capability with its own security surface — server-side
template execution risks SSTI-style issues once template content or render-context variables can
come from less-trusted input — and needs a deliberate sandboxing/allowed-filters design rather
than being bundled into standard CRUD.
