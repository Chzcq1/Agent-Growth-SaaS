---
name: design-critique-checklist
description: Checklist for reviewing or polishing this project's web UI so it reads as deliberately designed rather than default/AI-generated -- hierarchy, restraint, typography, motion, edge cases. Use before and after any UI change, especially "make it look nicer" requests.
---

# Design critique checklist

Adapted from the "impeccable" design-review pattern the user asked to bring into
this project. Not a full design system -- a discipline for reviewing what already
exists (this project has an established warm/cream + terracotta CSC brand palette;
never replace it wholesale, refine within it).

## What makes a UI read as "AI made it" (avoid these)

- Every section uses the same font size/weight -- no clear primary action or
  primary heading per view.
- Even, mechanical spacing everywhere (no rhythm -- some gaps should be tighter,
  some looser, to group related things and separate unrelated ones).
- Color used decoratively instead of to carry meaning (e.g. a badge color that
  doesn't map to a real state).
- Border-radius, shadow, and spacing values picked ad hoc per component instead
  of from a small consistent scale.
- No hover/focus/active state, or a generic browser default one.
- Motion that's either absent everywhere or applied uniformly everywhere (real
  craft uses motion selectively, tied to a state change the user should notice).

## Review pass -- work through in order

1. **Hierarchy**: for this view, what's the ONE thing the user should see first?
   Everything else should be visibly secondary (size, weight, or color contrast --
   not just "same style, smaller").
2. **Rhythm**: do related elements sit closer together than unrelated ones? Pick
   spacing from a small scale (e.g. 4/8/12/16/24/32px), not arbitrary values.
3. **Restraint**: does every color, shadow, and animation carry a real meaning
   (state, hierarchy, feedback)? Cut anything that's decoration only.
4. **States**: does every interactive element have a real hover/focus/active/
   disabled state that matches the rest of the design (not the browser default)?
5. **Edge cases**: empty state, long text overflow, loading state, error state --
   designed, not left to whatever the browser does by default.
6. **Motion**: is animation used only where it clarifies a state change (e.g. a
   "thinking" indicator, a result appearing) -- never decoration for its own sake?

## This project specifically (beauty_agent_system)

- Brand anchors already established: warm cream background, terracotta/orange
  accent (`#ff8a3d` family), agent "thinking cloud" + chip UI, chat-window layout
  with a pinned composer. Polish within this system -- don't introduce a
  different palette or visual metaphor without the user asking for a redesign.
- Styling lives in `app/static/css/streaming.css` (chat/office UI) -- check for an
  existing utility/variable before adding a new one-off value.
