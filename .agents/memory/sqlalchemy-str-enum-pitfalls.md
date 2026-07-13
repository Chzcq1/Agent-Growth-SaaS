---
name: SQLAlchemy + Postgres native ENUM with a Python str-Enum
description: Two related pitfalls when mapping a Python `class X(str, enum.Enum)` to a Postgres native ENUM column via SQLAlchemy -- storing the wrong label, and double-creating the type in a migration.
---

1. **Wrong stored value.** By default, SQLAlchemy's `Enum(MyEnum, ...)`
   stores the Python member's `.name`, not `.value`. For
   `class Status(str, enum.Enum): NEW = "New"`, inserting `Status.NEW`
   writes the literal string `"NEW"` -- if the Postgres type was created
   with labels like `'New'`, this fails with
   `invalid input value for enum ...: "NEW"`.

   Fix: pass `values_callable` so SQLAlchemy stores `.value` instead:
   ```python
   Enum(Status, name="status", values_callable=lambda cls: [m.value for m in cls])
   ```

2. **Double-creating the type in an Alembic migration.** If a migration
   both explicitly calls `my_enum.create(bind, checkfirst=True)` *and* then
   uses the same `Enum` object as a column type in `op.create_table(...)`,
   Postgres raises `type "x" already exists` -- `op.create_table` does not
   reliably check-first before creating an enum type referenced by a column.

   Fix: don't pre-create the type separately; just reference the `Enum(...)`
   object directly as a column type in `op.create_table(...)` and let that
   single call create it.

**Why:** both failures only show up against a real Postgres backend (SQLite
fallback used for import-time smoke tests won't catch either), so they
surface for the first time during the actual `alembic upgrade head` /
first-insert against the real DB.

**How to apply:** whenever mapping a `class X(str, enum.Enum)` to a native
Postgres enum column, set `values_callable` from the start, and in the
initial migration only create the enum type once (via `create_table`, not a
separate explicit `.create()` call before it).
