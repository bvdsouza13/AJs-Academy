---
name: Academy state evolution
description: Rules for safely extending the Academy's single JSONB family-state document.
---

For additive schema changes, recursively add only missing defaults; preserve existing list contents, customized settings, financial and family records, and unknown keys. Reject invalid structural containers instead of replacing them silently. Transformations such as renaming a field or changing its meaning need explicit, separately tested migrations.

**Why:** Additive upgrades must recover old records without losing user data, while a default merge alone cannot safely infer how to transform existing values.

**How to apply:** When adding optional settings or collections, extend defaults and keep the merge non-destructive. When an existing field changes shape or meaning, introduce a deliberate migration and test repeatability and preservation before relying on the new form.
