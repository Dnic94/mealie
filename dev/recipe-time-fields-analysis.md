# Recipe Time Fields: Bug Analysis & Fix Proposal

## Summary

All four recipe time fields (`totalTime`, `prepTime`, `cookTime`, `performTime`) are fully stored in the database and defined in the backend schema, but the UI has two bugs: one field is never shown, and one field carries the wrong label.

---

## Current State

| Field | Database | Schema | API Type | UI Displayed | UI Label |
|---|---|---|---|---|---|
| `totalTime` | ✓ | ✓ | ✓ | ✓ | "Total Time" ✓ |
| `prepTime` | ✓ | ✓ | ✓ | ✓ | "Prep Time" ✓ |
| `performTime` | ✓ | ✓ | ✓ | ✓ | **"Cook Time" — wrong** |
| `cookTime` | ✓ | ✓ | ✓ | **never shown** | — |

### Bug 1 — `cookTime` is completely invisible in the UI

`RecipeTimeCard.vue` has no `cookTime` prop. The field is also absent from the recipe editor and the print view. Any `cookTime` data stored in the database (e.g. from scraped recipes) is silently ignored.

### Bug 2 — `performTime` carries the wrong label

The translation key `recipe.perform-time` is set to **"Cook Time"** (`en-GB.json:519`). This is semantically incorrect according to the [schema.org Recipe spec](https://schema.org/Recipe):

- **`cookTime`** = passive time the dish spends cooking (oven, stove) without active involvement
- **`performTime`** = active hands-on time (chopping, stirring, assembling)

The label "Cook Time" belongs to `cookTime`, not `performTime`. A better label for `performTime` is **"Active Time"**.

---

## Affected Files

**Frontend only** — no backend or database changes are needed.

| File | Issue |
|---|---|
| `frontend/lang/messages/en-GB.json` | `perform-time` mislabeled "Cook Time"; no `cook-time` key exists |
| `frontend/components/Domain/Recipe/RecipeTimeCard.vue` | No `cookTime` prop, computed, or template block |
| `frontend/components/.../RecipePageInfoCard.vue` | `cookTime` not passed; `v-if` guard misses it |
| `frontend/components/.../RecipePageInfoEditor.vue` | No `cookTime` input field |
| `frontend/components/Domain/Recipe/RecipePrintView.vue` | `cookTime` not passed to `RecipeTimeCard` |

---

## Proposed Fix

### 1. Translation (`frontend/lang/messages/en-GB.json`)

```diff
- "perform-time": "Cook Time",
+ "perform-time": "Active Time",
  "prep-time": "Prep Time",
+ "cook-time": "Cook Time",
  "total-time": "Total Time",
```

> Only `en-GB.json` needs to be edited — all other locale files are managed via Crowdin.

---

### 2. `RecipeTimeCard.vue` — add `cookTime` prop and display block

```diff
 interface Props {
   prepTime?: string | null;
   totalTime?: string | null;
   performTime?: string | null;
+  cookTime?: string | null;
   color?: string;
   small?: boolean;
 }

 const props = withDefaults(defineProps<Props>(), {
   prepTime: null,
   totalTime: null,
   performTime: null,
+  cookTime: null,
   color: "accent custom-transparent",
   small: false,
 });

 const _showCards = computed(() => {
-  return [props.prepTime, props.totalTime, props.performTime].some(x => !isEmpty(x));
+  return [props.prepTime, props.totalTime, props.performTime, props.cookTime].some(x => !isEmpty(x));
 });

+const validateCookTime = computed(() => {
+  return !isEmpty(props.cookTime)
+    ? { name: i18n.t("recipe.cook-time"), value: props.cookTime }
+    : null;
+});

 const validatePerformTime = computed(() => {
   return !isEmpty(props.performTime)
     ? { name: i18n.t("recipe.perform-time"), value: props.performTime }
     : null;
 });
```

In the template, add `cookTime` into the second row between prep and perform time:

```diff
- <div v-if="validatePrepTime || validatePerformTime" ...>
+ <div v-if="validatePrepTime || validateCookTime || validatePerformTime" ...>

   <!-- after existing prepTime block -->
+  <v-divider v-if="validatePrepTime && validateCookTime" vertical class="mx-4" />
+  <div v-if="validateCookTime" class="d-flex flex-no-wrap my-1 align-center">
+    <v-icon :size="small ? 'small' : 'large'" left color="primary">
+      {{ $globals.icons.potSteam }}
+    </v-icon>
+    <p class="my-0">
+      <span class="font-weight-bold opacity-80">{{ validateCookTime.name }}</span>
+      <br>{{ validateCookTime.value }}
+    </p>
+  </div>

   <!-- update the divider guard before performTime -->
-  <v-divider v-if="validatePrepTime && validatePerformTime" vertical class="mx-4" />
+  <v-divider v-if="validatePerformTime && (validatePrepTime || validateCookTime)" vertical class="mx-4" />
```

The `potSteam` icon currently used on `performTime` should move to `cookTime` (a pot steaming = cooking). `performTime` could use the existing `chefHat` icon or `pending` (timer sand) icon — both are already imported in `icons.ts`.

---

### 3. `RecipePageInfoCard.vue` — pass `cookTime` and update guard

```diff
- <div v-if="recipe.prepTime || recipe.totalTime || recipe.performTime" class="mx-6">
+ <div v-if="recipe.prepTime || recipe.totalTime || recipe.performTime || recipe.cookTime" class="mx-6">
    <RecipeTimeCard
      :prep-time="recipe.prepTime"
      :total-time="recipe.totalTime"
      :perform-time="recipe.performTime"
+     :cook-time="recipe.cookTime"
    />
```

---

### 4. `RecipePageInfoEditor.vue` — add `cookTime` input field

```diff
  <v-text-field
    v-model="recipe.performTime"
    :label="$t('recipe.perform-time')"
    density="compact"
    variant="underlined"
  />
+ <v-text-field
+   v-model="recipe.cookTime"
+   :label="$t('recipe.cook-time')"
+   density="compact"
+   variant="underlined"
+ />
```

---

### 5. `RecipePrintView.vue` — pass `cookTime`

```diff
  <RecipeTimeCard
    :prep-time="recipe.prepTime"
    :total-time="recipe.totalTime"
    :perform-time="recipe.performTime"
+   :cook-time="recipe.cookTime"
    small
    color="white"
    class="ml-4"
  />
```

---

## Data Migration

**No database migration is required.** The `cook_time` column already exists and has been populated correctly by the recipe scraper for any imported recipes. The fix is frontend-only.

### Impact on existing recipes

| Recipe type | Effect after fix |
|---|---|
| Scraped recipes | `cookTime` becomes visible for the first time — no data loss |
| Manually entered recipes | The field previously labeled "Cook Time" (which stored to `performTime`) will now be labeled "Active Time". `cookTime` will be empty and can be filled in manually. |

### Optional: one-time data backfill

For users who manually entered data into the "Cook Time" field (actually `performTime`) and want that value to also appear as their `cookTime`, a voluntary SQL snippet could be offered:

```sql
UPDATE recipes
SET cook_time = perform_time
WHERE cook_time IS NULL AND perform_time IS NOT NULL;
```

**This should not be run automatically** — for scraped recipes, `performTime` and `cookTime` are intentionally different values. It is opt-in only, for users who know their data was manually entered.

---

## No Backend Changes Needed

The backend schema, API, and database are all already correct. This is a frontend-only oversight where `cookTime` was simply never wired up to the UI, and `performTime` inherited the "Cook Time" label by mistake.
