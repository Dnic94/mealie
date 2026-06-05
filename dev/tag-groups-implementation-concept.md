# Tag Groups (Tag-Gruppen) — Vollständiges Implementierungskonzept

## 1. Zusammenfassung

Tags in Mealie sollen in **Tag Groups** organisiert werden können. Jede Tag Group hat einen Namen, einen Slug und eine **Farbe**. Tags, die einer Gruppe zugewiesen sind, erhalten im Frontend die Gruppenfarbe als Chip-Hintergrund. In der Rezept-Ansicht werden Tags **vertikal nach Gruppe unterteilt** dargestellt. Beim Bearbeiten werden pro Gruppe nur die passenden Tags vorgeschlagen. Zusätzlich kann im Recipe Explorer nach Tag Groups gefiltert werden.

**Nicht im Scope:** Automatische Zuweisung von Tags zu Rezepten.

---

## 2. Ist-Zustand

### 2.1 Datenmodell

**Tag-Modell** (`mealie/db/models/recipe/tag.py`):
```python
class Tag(SqlAlchemyBase, BaseMixins):
    __tablename__ = "tags"
    id, group_id, name, slug
    # Relationships: group, recipes (M2M)
```

- Tags sind **flach** — keine Hierarchie, keine Metadaten außer `name`/`slug`
- Tags sind **group-scoped**: Unique Constraint auf `(slug, group_id)`
- Assoziationstabellen: `recipes_to_tags`, `plan_rules_to_tags`, `cookbooks_to_tags`

### 2.2 Schema

**Pydantic** (`mealie/schema/recipe/recipe_category.py`):
- `TagIn` → nur `name`
- `TagSave` → `name` + `group_id`
- `TagBase` → `id`, `name`, `slug`, `group_id`
- `TagOut` → vollständige Ausgabe
- `RecipeTagResponse` → Tag + zugehörige Rezepte

### 2.3 Frontend-Pfade

| Pfad | Zweck |
|------|-------|
| `/g/[groupSlug]/recipes/tags` | Tag-Verwaltung (CRUD, Liste) |
| `/g/[groupSlug]/recipes/categories` | Kategorie-Verwaltung |
| `/g/[groupSlug]` | Recipe Explorer mit Filtern (Tags, Categories, Tools, Foods) |

### 2.4 Betroffene Komponenten

| Komponente | Rolle |
|---|---|
| `RecipeOrganizerPage.vue` | Tag/Category-Verwaltungsseite (alphabetische Gruppen) |
| `RecipeOrganizerDialog.vue` | Erstellen/Bearbeiten-Dialog |
| `RecipeOrganizerSelector.vue` | Autocomplete-Selector im Rezept-Editor |
| `RecipePageOrganizers.vue` | Tag/Category-Anzeige auf der Rezeptseite |
| `RecipeChips.vue` | Chip-Darstellung (einheitlich `color="accent"`) |
| `RecipeExplorerPageSearchFilters.vue` | Filter-Sidebar im Recipe Explorer |
| `RecipeCard.vue` | Chip-Anzeige auf Rezeptkarten |

---

## 3. Ziel-Architektur

### 3.1 Neues Datenmodell: TagGroup

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│      Group       │ 1 ── n  │    TagGroup       │ 1 ── n  │       Tag        │
│  (Mealie-Gruppe) │─────────│                   │─────────│                  │
│                  │         │  id               │         │  id              │
│                  │         │  group_id (FK)     │         │  group_id (FK)   │
│                  │         │  name              │         │  tag_group_id    │
│                  │         │  slug              │         │  name            │
│                  │         │  color             │         │  slug            │
│                  │         │  position (sort)   │         │                  │
└──────────────────┘         └──────────────────┘         └──────────────────┘
```

- `TagGroup` ist **group-scoped** (genau wie Tags selbst)
- `Tag.tag_group_id` ist ein **nullable FK** auf `tag_groups.id` — Tags ohne Gruppe bleiben im „Unsortiert"-Bereich
- `TagGroup.color` speichert einen Hex-Wert (z.B. `#4CAF50`)
- `TagGroup.position` ermöglicht benutzerdefinierte Sortierung (Integer)

### 3.2 API-Endpunkte

Neuer Prefix: `/api/organizers/tag-groups`

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/tag-groups` | Alle Tag Groups (paginiert, mit Suche) |
| `POST` | `/tag-groups` | Tag Group erstellen |
| `GET` | `/tag-groups/{id}` | Einzelne Tag Group mit ihren Tags |
| `PUT` | `/tag-groups/{id}` | Tag Group aktualisieren (Name, Farbe, Position) |
| `DELETE` | `/tag-groups/{id}` | Tag Group löschen (Tags werden nicht gelöscht, nur `tag_group_id = NULL`) |
| `GET` | `/tag-groups/slug/{slug}` | Tag Group per Slug |

Öffentliche API analog: `/api/explore/groups/{group_slug}/organizers/tag-groups`

### 3.3 Frontend-Pfade

| Pfad | Zweck |
|------|-------|
| `/g/[groupSlug]/recipes/tags` | **Erweitert** — zeigt Tags gruppiert nach Tag Group, mit Verwaltung der Groups |

Da Tag Groups und Tags eng zusammenhängen, sollen beide auf **derselben Seite** verwaltet werden. Die bestehende Tag-Seite wird erweitert: oben ein Bereich für Tag Groups (CRUD), darunter Tags unterteilt nach Gruppen.

---

## 4. Detaillierte Implementierungs-Schritte

### Phase 1: Backend — Datenmodell & Migration

#### Schritt 1.1: SQLAlchemy-Modell `TagGroup`

**Neue Datei:** `mealie/db/models/recipe/tag_group.py`

```python
import sqlalchemy as sa
import sqlalchemy.orm as orm
from slugify import slugify
from sqlalchemy.orm import Mapped, mapped_column, validates

from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
from mealie.db.models._model_utils import guid

class TagGroup(SqlAlchemyBase, BaseMixins):
    __tablename__ = "tag_groups"
    __table_args__ = (
        sa.UniqueConstraint("slug", "group_id", name="tag_groups_slug_group_id_key"),
    )

    id: Mapped[guid.GUID] = mapped_column(guid.GUID, primary_key=True, default=guid.GUID.generate)
    group_id: Mapped[guid.GUID] = mapped_column(guid.GUID, sa.ForeignKey("groups.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(sa.String, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String, index=True, nullable=False)
    color: Mapped[str | None] = mapped_column(sa.String, nullable=True)  # Hex, z.B. "#4CAF50"
    position: Mapped[int] = mapped_column(sa.Integer, default=0)

    # Relationships
    group: Mapped["Group"] = orm.relationship("Group", back_populates="tag_groups", foreign_keys=[group_id])
    tags: Mapped[list["Tag"]] = orm.relationship("Tag", back_populates="tag_group")

    @validates("name")
    def validate_name(self, key, name):
        assert name != ""
        return name

    def __init__(self, name, group_id, **kwargs) -> None:
        self.group_id = group_id
        self.name = name.strip()
        self.slug = slugify(self.name)
        self.color = kwargs.get("color")
        self.position = kwargs.get("position", 0)
```

#### Schritt 1.2: Tag-Modell erweitern

**Datei:** `mealie/db/models/recipe/tag.py`

```diff
+ from .tag_group import TagGroup

  class Tag(SqlAlchemyBase, BaseMixins):
      # ... bestehende Felder ...
+     tag_group_id: Mapped[guid.GUID | None] = mapped_column(
+         guid.GUID, sa.ForeignKey("tag_groups.id"), nullable=True, index=True
+     )
+     tag_group: Mapped["TagGroup | None"] = orm.relationship(
+         "TagGroup", back_populates="tags", foreign_keys=[tag_group_id]
+     )
```

#### Schritt 1.3: Group-Modell erweitern

**Datei:** `mealie/db/models/group/group.py` — Relationship hinzufügen:

```python
tag_groups: Mapped[list["TagGroup"]] = orm.relationship("TagGroup", back_populates="group")
```

#### Schritt 1.4: `__init__.py` Exporte

**Datei:** `mealie/db/models/recipe/__init__.py` — `TagGroup` importieren und exportieren.

#### Schritt 1.5: Alembic-Migration

```bash
task py:migrate -- "add tag_groups table and tag.tag_group_id column"
```

**Migration erzeugt:**
1. `CREATE TABLE tag_groups` mit Spalten `id, group_id, name, slug, color, position`
2. `ALTER TABLE tags ADD COLUMN tag_group_id` (nullable FK)
3. Unique Constraint `tag_groups_slug_group_id_key`
4. Index auf `tags.tag_group_id`

**Kein Datenverlust** — bestehende Tags behalten `tag_group_id = NULL` (werden als „Ungrouped" behandelt).

---

### Phase 2: Backend — Schemas

#### Schritt 2.1: Pydantic-Schemas für TagGroup

**Neue Datei:** `mealie/schema/recipe/recipe_tag_group.py`

```python
from pydantic import UUID4, ConfigDict
from mealie.schema._mealie import MealieModel

class TagGroupIn(MealieModel):
    name: str
    color: str | None = None
    position: int = 0

class TagGroupSave(TagGroupIn):
    group_id: UUID4

class TagGroupBase(TagGroupIn):
    id: UUID4
    group_id: UUID4 | None = None
    slug: str
    model_config = ConfigDict(from_attributes=True)

class TagGroupOut(TagGroupSave):
    id: UUID4
    slug: str
    model_config = ConfigDict(from_attributes=True)

class TagGroupSummary(TagGroupBase):
    """Tag group with list of tags"""
    tags: list["RecipeTag"] = []
    model_config = ConfigDict(from_attributes=True)

# Deferred import to avoid circular dependency
from mealie.schema.recipe.recipe import RecipeTag  # noqa: E402
TagGroupSummary.model_rebuild()
```

#### Schritt 2.2: Tag-Schemas erweitern

**Datei:** `mealie/schema/recipe/recipe_category.py`

```diff
  class TagIn(CategoryIn):
-     pass
+     tag_group_id: UUID4 | None = None

  class TagBase(CategoryBase):
-     pass
+     tag_group_id: UUID4 | None = None
```

**Datei:** `mealie/schema/recipe/recipe.py` — `RecipeTag` erweitern:

```diff
  class RecipeTag(MealieModel):
      id: UUID4 | None = None
      group_id: UUID4 | None = None
      name: str
      slug: str
+     tag_group_id: UUID4 | None = None
```

#### Schritt 2.3: Code-Generierung

```bash
task dev:generate
```

Dies aktualisiert die TypeScript-Typen in `frontend/lib/api/types/` und die Schema-Exporte.

---

### Phase 3: Backend — Repository & Routes

#### Schritt 3.1: TagGroup-Repository

**Datei:** `mealie/repos/repository_factory.py` — neues Repository:

```python
class RepositoryTagGroups(GroupRepositoryGeneric[TagGroupOut, TagGroup]):
    pass
```

**Datei:** `mealie/repos/all_repositories.py` — registrieren:

```python
@cached_property
def tag_groups(self) -> RepositoryTagGroups:
    return RepositoryTagGroups(self.session, ...)
```

#### Schritt 3.2: TagGroup-Controller

**Neue Datei:** `mealie/routes/organizers/controller_tag_groups.py`

Analog zu `controller_tags.py`:
- `GET /tag-groups` — paginiert + Suche
- `POST /tag-groups` — erstellen
- `GET /tag-groups/{id}` — mit Tags (Response: `TagGroupSummary`)
- `PUT /tag-groups/{id}` — aktualisieren
- `DELETE /tag-groups/{id}` — löschen (setzt `tag_group_id = NULL` bei zugehörigen Tags)
- `GET /tag-groups/slug/{slug}` — per Slug

#### Schritt 3.3: Route registrieren

**Datei:** `mealie/routes/organizers/__init__.py`:

```diff
+ from .controller_tag_groups import router as tag_groups_router
  router = APIRouter(prefix="/organizers")
  router.include_router(tags_router)
  router.include_router(categories_router)
+ router.include_router(tag_groups_router)
```

#### Schritt 3.4: Explore/Public API

**Datei:** `mealie/routes/explore/controller_public_organizers.py` — öffentliche TagGroup-Endpunkte analog hinzufügen.

#### Schritt 3.5: Event-Typen

**Datei:** `mealie/services/event_bus_service/event_types.py`:

```python
tag_group_created = auto()
tag_group_updated = auto()
tag_group_deleted = auto()
```

Plus `EventTagGroupData` Klasse.

#### Schritt 3.6: Tag-Controller erweitern

**Datei:** `mealie/routes/organizers/controller_tags.py`:
- `TagIn` akzeptiert nun `tag_group_id`
- Beim Erstellen/Aktualisieren wird `tag_group_id` durchgereicht
- Neuer Endpunkt oder Query-Parameter: `GET /tags?tag_group_id={id}` — Tags nach Gruppe filtern

#### Schritt 3.7: Recipe-Filter erweitern

**Datei:** `mealie/repos/repository_recipes.py`:

Neue Parameter in `page_all()` und `_build_recipe_filter()`:

```python
def page_all(self, ..., tag_groups: list[UUID4 | str] | None = None, require_all_tag_groups=True, ...):
    ...

def _build_recipe_filter(self, ..., tag_groups: list[UUID4] | None = None, require_all_tag_groups=True, ...):
    if tag_groups:
        if require_all_tag_groups:
            for tg_id in tag_groups:
                fltr.append(RecipeModel.tags.any(Tag.tag_group_id == tg_id))
        else:
            fltr.append(RecipeModel.tags.any(Tag.tag_group_id.in_(tag_groups)))
```

**Datei:** `mealie/routes/recipe/recipe_crud_routes.py` — `tag_groups` Query-Parameter hinzufügen.

---

### Phase 4: Frontend — API-Client & Stores

#### Schritt 4.1: TagGroup API-Client

**Neue Datei:** `frontend/lib/api/user/organizer-tag-groups.ts`

```typescript
export class TagGroupsAPI extends BaseCRUDAPI<TagGroupIn, TagGroupOut> {
  baseRoute = `${prefix}/tag-groups`;
  itemRoute = (id: string) => `${prefix}/tag-groups/${id}`;

  async bySlug(slug: string) {
    return await this.requests.get<TagGroupSummary>(`${prefix}/tag-groups/slug/${slug}`);
  }
}
```

#### Schritt 4.2: API-Client registrieren

**Datei:** `frontend/lib/api/user/` — in die API-Factory eintragen (analog zu Tags/Categories).

#### Schritt 4.3: TagGroup Store

**Neue Datei:** `frontend/composables/store/use-tag-group-store.ts`

```typescript
const store: Ref<TagGroupOut[]> = ref([]);
const loading = ref(false);

export const useTagGroupStore = function (i18n?: Composer) {
  const api = useUserApi(i18n);
  return useStore<TagGroupOut>("tagGroup", store, loading, api.tagGroups);
};

export const usePublicTagGroupStore = function (groupSlug: string, i18n?: Composer) {
  const api = usePublicExploreApi(groupSlug, i18n).explore;
  return useReadOnlyStore<TagGroupOut>("tagGroup", store, publicLoading, api.tagGroups);
};
```

Registrierung in `frontend/composables/store/index.ts`.

---

### Phase 5: Frontend — Tag-Verwaltungsseite erweitern

#### Schritt 5.1: Tags-Seite umbauen

**Datei:** `frontend/pages/g/[groupSlug]/recipes/tags/index.vue`

Die bestehende Seite nutzt bisher nur `RecipeOrganizerPage`. Umbauen zu einer zweigeteilten Ansicht:

1. **Oberer Bereich: Tag Groups verwalten**
   - Horizontale Chip-Leiste oder Karten mit den Tag Groups (Name + Farbe)
   - Buttons: Erstellen, Bearbeiten, Löschen, Sortieren (Drag & Drop optional)
   - Klick auf eine Tag Group scrollt zur zugehörigen Sektion unten

2. **Unterer Bereich: Tags nach Gruppe**
   - Vertikale Sektionen, eine pro Tag Group (Titel = Gruppenname, Hintergrundakzent = Gruppenfarbe)
   - Letzte Sektion: „Ungrouped" für Tags ohne Gruppe
   - Innerhalb jeder Sektion: alphabetische Tag-Liste (wie bisherige `RecipeOrganizerPage`)
   - Beim Erstellen eines Tags: Dropdown zur Auswahl der Tag Group
   - Beim Bearbeiten: Tag Group ist änderbar

#### Schritt 5.2: `RecipeOrganizerDialog.vue` erweitern

Optionales Tag-Group-Dropdown-Feld (nur für `itemType === "tag"`):
- Dropdown mit allen Tag Groups
- Vorausgewählt wenn aus einer Gruppen-Sektion heraus erstellt
- Nullable — „Keine Gruppe" als Option

#### Schritt 5.3: Neue Komponente `TagGroupManager.vue`

**Neue Datei:** `frontend/components/Domain/Recipe/TagGroupManager.vue`

- CRUD-Operationen für Tag Groups
- Color Picker für die Gruppenfarbe (Vuetify `v-color-picker` oder vorgegebene Palette)
- Drag & Drop für Position/Reihenfolge (optional, kann nachgelagert sein)
- Inline-Bearbeitung von Name und Farbe

---

### Phase 6: Frontend — Rezept-Ansicht & Editor

#### Schritt 6.1: `RecipePageOrganizers.vue` umbauen

**Datei:** `frontend/components/Domain/Recipe/RecipePage/RecipePageParts/RecipePageOrganizers.vue`

Statt einer einzigen Tag-Sektion → **dynamische Sektionen pro Tag Group**:

```vue
<!-- Bestehend: Categories -->
<v-card v-if="recipe.recipeCategory.length > 0 || isEditForm">
  ...
</v-card>

<!-- NEU: Tags gruppiert nach Tag Group -->
<v-card
  v-for="tagGroup in tagGroupsWithTags"
  :key="tagGroup.id"
  class="mt-4"
>
  <v-card-title class="py-2" :style="{ borderLeft: `4px solid ${tagGroup.color}` }">
    {{ tagGroup.name }}
  </v-card-title>
  <v-divider class="mx-2" />
  <v-card-text>
    <RecipeOrganizerSelector
      v-if="isEditForm"
      v-model="groupedTags[tagGroup.id]"
      :return-object="true"
      selector-type="tags"
      :filter-by-tag-group="tagGroup.id"
    />
    <RecipeChips
      v-else
      :items="groupedTags[tagGroup.id]"
      url-prefix="tags"
      :chip-color="tagGroup.color"
    />
  </v-card-text>
</v-card>

<!-- Ungrouped Tags -->
<v-card v-if="ungroupedTags.length > 0 || isEditForm" class="mt-4">
  <v-card-title class="py-2">{{ $t("tag.tags") }}</v-card-title>
  ...
</v-card>
```

**Computed Properties:**
- `tagGroupsWithTags` — Tag Groups sortiert nach `position`, die mindestens einen Tag in diesem Rezept haben (oder im Edit-Modus: alle Tag Groups)
- `groupedTags` — reactive Map von `tagGroupId → RecipeTag[]`
- `ungroupedTags` — Tags mit `tag_group_id === null`

#### Schritt 6.2: `RecipeOrganizerSelector.vue` erweitern

Neuer optionaler Prop: `filterByTagGroup`:
- Wenn gesetzt, filtert die Autocomplete-Liste auf Tags, die diese `tag_group_id` haben
- Im Edit-Modus werden so pro Sektion nur passende Tags vorgeschlagen

```diff
  interface Props {
    selectorType: RecipeOrganizer;
+   filterByTagGroup?: string | null;
    showAdd?: boolean;
    showLabel?: boolean;
  }
```

Filter-Logik:
```typescript
const filteredItems = computed(() => {
  if (props.filterByTagGroup && props.selectorType === "tags") {
    return storeItems.value.filter(tag => tag.tagGroupId === props.filterByTagGroup);
  }
  return storeItems.value;
});
```

#### Schritt 6.3: `RecipeChips.vue` erweitern

Neuer optionaler Prop: `chipColor`:

```diff
  interface Props {
    items?: RecipeCategory[] | RecipeTag[] | RecipeTool[];
+   chipColor?: string | null;
    ...
  }
```

```diff
  <v-chip
-   color="accent"
+   :color="chipColor || 'accent'"
    ...
  >
```

Alternativ/Zusätzlich: Wenn Tags ein `tag_group_id` haben, die Farbe automatisch aus dem Tag-Group-Store resolven:

```typescript
function getChipColor(item: RecipeTag) {
  if ('tagGroupId' in item && item.tagGroupId) {
    const group = tagGroupStore.value.find(g => g.id === item.tagGroupId);
    return group?.color || 'accent';
  }
  return props.chipColor || 'accent';
}
```

#### Schritt 6.4: `RecipeCard.vue` anpassen

Die Tags auf Rezeptkarten bekommen ebenfalls die Gruppenfarbe. Da `RecipeChips` erweitert wird, funktioniert das automatisch, sofern die Farb-Resolution dort implementiert ist.

---

### Phase 7: Frontend — Recipe Explorer Filter

#### Schritt 7.1: `RecipeExplorerPageSearchFilters.vue` erweitern

**Datei:** `frontend/components/Domain/Recipe/RecipeExplorerPage/RecipeExplorerPageParts/RecipeExplorerPageSearchFilters.vue`

Neuen Filter-Block für Tag Groups hinzufügen:

```vue
<!-- Tag Group Filter -->
<SearchFilter
  v-if="tagGroups"
  v-model="selectedTagGroups"
  v-model:require-all="state.requireAllTagGroups"
  :items="tagGroups"
>
  <v-icon start>{{ $globals.icons.tagGroup }}</v-icon>
  {{ $t("tag.tag-groups") }}
</SearchFilter>
```

#### Schritt 7.2: `use-recipe-explorer-search.ts` erweitern

- Neuer State: `selectedTagGroups`, `requireAllTagGroups`
- URL Query-Parameter: `tagGroups`, `requireAllTagGroups`
- In `RecipeSearchQuery` aufnehmen
- An Backend durchreichen

#### Schritt 7.3: Backend Query-Parameter

**Datei:** `mealie/routes/recipe/recipe_crud_routes.py`:

```python
@router.get("")
async def get_recipes(
    ...
    tag_groups: list[UUID4 | str] | None = Query(None),
    require_all_tag_groups: bool = True,
    ...
):
```

---

### Phase 8: i18n

#### Schritt 8.1: Translations (nur `en-GB.json`)

```json
{
  "tag": {
    "tag": "Tag",
    "tags": "Tags",
    "tag-groups": "Tag Groups",
    "tag-group": "Tag Group",
    "tag-group-name": "Tag Group Name",
    "tag-group-color": "Tag Group Color",
    "tag-group-created": "Tag Group created",
    "tag-group-updated": "Tag Group updated",
    "tag-group-deleted": "Tag Group deleted",
    "tag-group-creation-failed": "Tag Group creation failed",
    "tag-group-update-failed": "Tag Group update failed",
    "tag-group-deletion-failed": "Tag Group deletion failed",
    "create-a-tag-group": "Create a Tag Group",
    "ungrouped": "Ungrouped",
    "tag-group-filter": "Tag Group Filter",
    ...
  }
}
```

---

## 5. Datenmigration — Strategie für bestehende Tags

### 5.1 Standard-Migration (automatisch)

Bei der Alembic-Migration:
1. `tag_groups`-Tabelle wird erstellt
2. `tags.tag_group_id`-Spalte wird hinzugefügt (nullable, default `NULL`)
3. **Alle bestehenden Tags behalten `tag_group_id = NULL`** → werden als „Ungrouped" angezeigt

**Kein Datenverlust. Kein Breaking Change.** Bestehende Installationen funktionieren exakt wie vorher — Tags erscheinen einfach im „Ungrouped"-Bereich.

### 5.2 Workaround-Migration (optional, manuell)

Für Nutzer, die bereits den `Typ:Tag`-Workaround verwenden (z.B. `Diät:Vegan`, `Herkunft:Deutschland`):

**Optionales Migrations-Script** (nicht in Alembic, sondern als eigenständiges Tool oder Admin-Aktion):

```python
"""
Parst bestehende Tags im Format "Prefix:Name" und erstellt
automatisch Tag Groups aus den Prefixen.
"""
def migrate_prefixed_tags(session, group_id):
    tags = session.query(Tag).filter(Tag.group_id == group_id).all()

    prefix_map = {}  # prefix -> TagGroup
    for tag in tags:
        if ":" in tag.name:
            prefix, name = tag.name.split(":", 1)
            prefix = prefix.strip()
            name = name.strip()

            if prefix not in prefix_map:
                tag_group = TagGroup(name=prefix, group_id=group_id)
                session.add(tag_group)
                session.flush()
                prefix_map[prefix] = tag_group

            tag.tag_group_id = prefix_map[prefix].id
            tag.name = name  # Prefix aus Name entfernen
            tag.slug = slugify(name)

    session.commit()
```

**Probleme bei dieser Migration:**

| Problem | Lösung |
|---------|--------|
| Slug-Kollision: `Diät:Vegan` und `Herkunft:Vegan` → beide Slugs wären `vegan` | Slug bleibt unique innerhalb `(slug, group_id)`, nicht innerhalb Tag Groups. Falls Kollision: Suffix anfügen oder User-Entscheidung |
| Tags ohne `:` im Namen | Bleiben unverändert in „Ungrouped" |
| Tags mit mehreren `:` (z.B. `Quelle:Website:URL`) | Nur am ersten `:` splitten |
| Meal Plan Rules und Cookbooks referenzieren Tags | Referenzen bleiben intakt (Tag-ID ändert sich nicht) |
| Rezept-Tag-Zuordnungen | Bleiben intakt (M2M-Tabelle referenziert Tag-IDs) |

### 5.3 Admin-UI-Option

Idealerweise als **Admin-Button** auf der Tag-Verwaltungsseite:
- „Import Tag Groups from prefixed tags" (z.B. `Typ:Tag` Format)
- Preview-Dialog: zeigt was migriert würde
- Bestätigungs-Button
- Rückgängig nicht automatisch möglich → Warnung anzeigen

---

## 6. Potenzielle Probleme & Lösungen

### 6.1 Slug-Einzigartigkeit

**Problem:** Unique Constraint ist `(slug, group_id)` auf Tag-Ebene. Wenn `Diät:Vegan` und `Herkunft:Vegan` zu `vegan` werden, kollidieren die Slugs.

**Lösung:** Keine Änderung nötig. Die Tags behalten ihre bestehenden Slugs (`diat-vegan`, `herkunft-vegan`). Nur bei der Prefix-Migration werden Slugs neu generiert — dort muss auf Kollisionen geprüft werden. Alternativ: Slug bleibt `diat-vegan` und nur der `name` wird auf `Vegan` gesetzt.

**Empfehlung:** Bei der optionalen Prefix-Migration den alten Slug beibehalten, um URL-Stabilität zu gewährleisten. Nur den angezeigten Namen bereinigen.

### 6.2 API-Kompatibilität

**Problem:** Bestehende API-Clients (z.B. mobile Apps, Integrationen) senden `TagIn` ohne `tag_group_id`.

**Lösung:** `tag_group_id` ist nullable und optional. Bestehende API-Aufrufe funktionieren unverändert.

### 6.3 Performance

**Problem:** Rezept-Ansicht muss Tag Groups auflösen.

**Lösung:** `selectinload(Tag.tag_group)` in den RecipeSummary Loader Options hinzufügen. Alternativ: Tag Group ID und Farbe als flache Felder im RecipeTag-Schema mitsenden, um N+1-Queries zu vermeiden.

**Empfehlung:** `RecipeTag` um `tag_group_color` und `tag_group_name` erweitern (flache Felder, aus ORM loaded). So braucht das Frontend keinen separaten Store-Lookup pro Tag:

```python
class RecipeTag(MealieModel):
    id: UUID4 | None = None
    name: str
    slug: str
    tag_group_id: UUID4 | None = None
    tag_group_name: str | None = None   # denormalisiert
    tag_group_color: str | None = None  # denormalisiert
```

### 6.4 Tag Group-Löschung

**Problem:** Was passiert mit Tags wenn ihre Gruppe gelöscht wird?

**Lösung:** `ON DELETE SET NULL` auf dem FK. Tags werden nicht gelöscht, sondern zu „Ungrouped".

### 6.5 Recipe Explorer Filter-Interaktion

**Problem:** Filtern nach Tag Group UND einzelnen Tags gleichzeitig.

**Lösung:** Beide Filter koexistieren. Tag Group-Filter findet Rezepte, die mindestens einen Tag aus der Gruppe haben. Tag-Filter findet Rezepte mit dem exakten Tag. Beide werden per AND kombiniert.

### 6.6 Cookbooks und Meal Plan Rules

**Problem:** Cookbooks und Meal Plan Rules referenzieren Tags direkt. Brauchen sie auch Tag Group-Support?

**Lösung:** Nicht sofort. Die bestehende Tag-Referenz funktioniert weiterhin. Tag Group-Filter für Cookbooks/Meal Plans kann als Follow-up implementiert werden.

---

## 7. Reihenfolge der Implementierung

### Sprint 1: Backend-Grundlage
1. ☐ SQLAlchemy-Modell `TagGroup` erstellen
2. ☐ `Tag`-Modell um `tag_group_id` erweitern
3. ☐ Alembic-Migration generieren und prüfen (SQLite + Postgres)
4. ☐ Pydantic-Schemas für `TagGroup` erstellen
5. ☐ `TagIn`/`TagBase`/`RecipeTag` um `tag_group_id` erweitern
6. ☐ Repository für `TagGroup` erstellen
7. ☐ Controller für `TagGroup` CRUD erstellen
8. ☐ Tag-Controller um `tag_group_id` Handling erweitern
9. ☐ Event-Typen hinzufügen
10. ☐ Public/Explore API für Tag Groups
11. ☐ `task dev:generate` ausführen
12. ☐ `task py:check` — alle Tests müssen grün sein

### Sprint 2: Frontend Tag Group Verwaltung
13. ☐ API-Client `TagGroupsAPI` erstellen
14. ☐ Store `useTagGroupStore` erstellen
15. ☐ i18n-Keys hinzufügen (nur `en-GB.json`)
16. ☐ Tag-Verwaltungsseite erweitern (gruppierte Ansicht + Tag Group CRUD)
17. ☐ `RecipeOrganizerDialog.vue` um Tag Group-Auswahl erweitern
18. ☐ Icon für Tag Groups in `icons.ts` hinzufügen

### Sprint 3: Frontend Rezept-Integration
19. ☐ `RecipeChips.vue` um `chipColor` / automatische Farb-Resolution erweitern
20. ☐ `RecipePageOrganizers.vue` auf gruppierte Darstellung umbauen
21. ☐ `RecipeOrganizerSelector.vue` um `filterByTagGroup` Prop erweitern
22. ☐ `RecipeCard.vue` — Tag-Farben testen

### Sprint 4: Recipe Explorer Filter
23. ☐ `_build_recipe_filter()` um Tag Group-Filter erweitern
24. ☐ Recipe CRUD Route um `tag_groups` Query-Parameter erweitern
25. ☐ `use-recipe-explorer-search.ts` um Tag Group State erweitern
26. ☐ `RecipeExplorerPageSearchFilters.vue` um Tag Group-Filter erweitern

### Sprint 5: Migration & Polish
27. ☐ Optionales Prefix-Migrations-Script erstellen
28. ☐ Admin-UI-Aktion für Prefix-Migration (optional)
29. ☐ Vollständige Tests (Backend + Frontend)
30. ☐ `task py:check` + `task ui:check`

---

## 8. Dateien-Übersicht (Neue & Geänderte)

### Neue Dateien

| Datei | Beschreibung |
|---|---|
| `mealie/db/models/recipe/tag_group.py` | SQLAlchemy-Modell |
| `mealie/schema/recipe/recipe_tag_group.py` | Pydantic-Schemas |
| `mealie/routes/organizers/controller_tag_groups.py` | API-Controller |
| `mealie/alembic/versions/xxxx_add_tag_groups.py` | DB-Migration |
| `frontend/lib/api/user/organizer-tag-groups.ts` | API-Client |
| `frontend/composables/store/use-tag-group-store.ts` | Composable Store |
| `frontend/components/Domain/Recipe/TagGroupManager.vue` | Tag Group CRUD UI |

### Geänderte Dateien

| Datei | Änderung |
|---|---|
| `mealie/db/models/recipe/tag.py` | `tag_group_id` FK + Relationship |
| `mealie/db/models/recipe/__init__.py` | Export TagGroup |
| `mealie/db/models/group/group.py` | tag_groups Relationship |
| `mealie/schema/recipe/recipe_category.py` | `tag_group_id` in TagIn/TagBase |
| `mealie/schema/recipe/recipe.py` | `tag_group_id/name/color` in RecipeTag |
| `mealie/repos/repository_factory.py` | RepositoryTagGroups |
| `mealie/repos/all_repositories.py` | tag_groups Property |
| `mealie/repos/repository_recipes.py` | Tag Group Filter in `_build_recipe_filter()` |
| `mealie/routes/organizers/__init__.py` | tag_groups Router |
| `mealie/routes/recipe/recipe_crud_routes.py` | tag_groups Query-Parameter |
| `mealie/routes/explore/controller_public_organizers.py` | Public Tag Group Endpunkte |
| `mealie/services/event_bus_service/event_types.py` | Neue Event-Typen |
| `frontend/lib/api/types/non-generated.ts` | (optional) Organizer Enum |
| `frontend/composables/store/index.ts` | TagGroup Store Export |
| `frontend/composables/use-recipe-explorer-search.ts` | Tag Group Filter State |
| `frontend/components/Domain/Recipe/RecipeChips.vue` | Farbiger Chip-Hintergrund |
| `frontend/components/Domain/Recipe/RecipeOrganizerSelector.vue` | `filterByTagGroup` Prop |
| `frontend/components/Domain/Recipe/RecipeOrganizerDialog.vue` | Tag Group Dropdown |
| `frontend/components/Domain/Recipe/RecipePageOrganizers.vue` | Gruppierte Darstellung |
| `frontend/components/Domain/Recipe/RecipeExplorerPage/.../SearchFilters.vue` | Tag Group Filter |
| `frontend/pages/g/[groupSlug]/recipes/tags/index.vue` | Gruppierte Verwaltungsseite |
| `frontend/lang/messages/en-GB.json` | Neue i18n-Keys |
