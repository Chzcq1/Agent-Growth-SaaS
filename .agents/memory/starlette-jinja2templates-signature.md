---
name: Starlette Jinja2Templates.TemplateResponse signature change
description: Newer starlette (seen at 1.3.1) requires request as the first positional argument to TemplateResponse; the old FastAPI-tutorial style of passing request inside the context dict is now silently wrong and produces a confusing error deep in Jinja2's template cache.
---

Old (now wrong on newer starlette) style:

```python
templates.TemplateResponse("page.html", {"request": request, "foo": foo})
```

Correct current signature:

```python
templates.TemplateResponse(request, "page.html", {"foo": foo})
```

**Why:** if you pass the old style, the template *name* string lands in the
`request` parameter and the context *dict* lands in the `name` parameter.
Jinja2 then tries to build a cache key `(weakref(loader), name)` where `name`
is actually a dict, raising `TypeError: unhashable type: 'dict'` deep inside
`jinja2/utils.py`'s LRU cache -- a very misleading error that looks like a
templating engine bug rather than an argument-order bug.

**How to apply:** whenever you see `TypeError: unhashable type: 'dict'`
coming out of `jinja2.environment._load_template` / `self.cache.get(...)`
during a Starlette/FastAPI `TemplateResponse` call, check the argument order
first before suspecting Jinja2 itself. Always write new template routes with
`request` as the first positional argument.
