<template>
  <v-container>
    <!-- Create Tag Group Dialog -->
    <BaseDialog
      v-model="dialogs.createGroup"
      :title="$t('tag.create-a-tag-group')"
      :icon="$globals.icons.tagGroups"
      can-confirm
      @confirm="createGroup"
    >
      <v-card-text>
        <v-text-field
          v-model="groupForm.name"
          :label="$t('tag.tag-group-name')"
          autofocus
        />
        <InputColor v-model="groupForm.color" />
        <v-text-field
          v-model.number="groupForm.position"
          :label="$t('tag.tag-group-position')"
          type="number"
          min="0"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Update Tag Group Dialog -->
    <BaseDialog
      v-if="updateGroupTarget"
      v-model="dialogs.updateGroup"
      :title="$t('data-pages.tag-groups.edit-tag-group')"
      :icon="$globals.icons.tagGroups"
      can-confirm
      @confirm="updateGroup"
    >
      <v-card-text>
        <v-text-field
          v-model="updateGroupTarget.name"
          :label="$t('tag.tag-group-name')"
          autofocus
        />
        <InputColor v-model="updateGroupTarget.color" />
        <v-text-field
          v-model.number="updateGroupTarget.position"
          :label="$t('tag.tag-group-position')"
          type="number"
          min="0"
        />
      </v-card-text>
    </BaseDialog>

    <!-- Delete Tag Group Dialog -->
    <BaseDialog
      v-if="deleteGroupTarget"
      v-model="dialogs.deleteGroup"
      :title="$t('general.delete-with-name', { name: $t('tag.tag-group') })"
      color="error"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="deleteGroup"
    >
      <v-card-text>
        <p>{{ $t('general.confirm-delete-generic-with-name', { name: $t('tag.tag-group') }) }}</p>
        <p class="mt-4 mb-0 ml-4">
          {{ deleteGroupTarget.name }}
        </p>
      </v-card-text>
    </BaseDialog>

    <!-- Create Tag Dialog -->
    <BaseDialog
      v-model="dialogs.createTag"
      :title="$t('tag.create-a-tag')"
      :icon="$globals.icons.tags"
      can-confirm
      @confirm="createTag"
    >
      <v-card-text>
        <v-text-field
          v-model="tagForm.name"
          :label="$t('tag.tag-name')"
          autofocus
        />
        <v-select
          v-model="tagForm.tagGroupId"
          :items="sortedGroups"
          :label="$t('tag.tag-group')"
          :prepend-inner-icon="$globals.icons.tagGroups"
          item-title="name"
          item-value="id"
          clearable
        />
      </v-card-text>
    </BaseDialog>

    <!-- Update Tag Dialog -->
    <BaseDialog
      v-if="updateTagTarget"
      v-model="dialogs.updateTag"
      :title="$t('data-pages.tags.edit-tag')"
      :icon="$globals.icons.tags"
      can-confirm
      @confirm="updateTag"
    >
      <v-card-text>
        <v-text-field
          v-model="updateTagTarget.name"
          :label="$t('tag.tag-name')"
          autofocus
        />
        <v-select
          v-model="updateTagTarget.tagGroupId"
          :items="sortedGroups"
          :label="$t('tag.tag-group')"
          :prepend-inner-icon="$globals.icons.tagGroups"
          item-title="name"
          item-value="id"
          clearable
        />
      </v-card-text>
    </BaseDialog>

    <!-- Delete Tag Dialog -->
    <BaseDialog
      v-if="deleteTagTarget"
      v-model="dialogs.deleteTag"
      :title="$t('general.delete-with-name', { name: $t('tag.tag') })"
      color="error"
      :icon="$globals.icons.alertCircle"
      can-confirm
      @confirm="deleteTag"
    >
      <v-card-text>
        <p>{{ $t('general.confirm-delete-generic-with-name', { name: $t('tag.tag') }) }}</p>
        <p class="mt-4 mb-0 ml-4">
          {{ deleteTagTarget.name }}
        </p>
      </v-card-text>
    </BaseDialog>

    <!-- Search -->
    <v-row density="comfortable">
      <v-col>
        <v-text-field
          v-model="searchString"
          variant="outlined"
          autofocus
          color="primary accent-3"
          :placeholder="$t('search.search-placeholder')"
          :prepend-inner-icon="$globals.icons.search"
          clearable
        />
      </v-col>
    </v-row>

    <!-- Toolbar with two create buttons -->
    <v-row
      color="transparent"
      flat
      class="mt-n1 mb-2 px-3 rounded align-center position-relative w-100 left-0 top-0"
    >
      <v-icon size="large" start>
        {{ $globals.icons.tags }}
      </v-icon>
      <v-toolbar-title class="headline">
        {{ $t("sidebar.tags") }}
      </v-toolbar-title>
      <v-spacer />
      <BaseButton
        create
        secondary
        :text="$t('tag.tag-group')"
        class="mr-2"
        @click="openCreateGroupDialog"
      />
      <BaseButton
        create
        :text="$t('tag.tag')"
        @click="openCreateTagDialog()"
      />
    </v-row>

    <!-- Tag group sections -->
    <template v-for="group in visibleGroups" :key="group.id">
      <section class="my-4">
        <!-- Section header: group name with color accent + quick add + context menu -->
        <div class="d-flex align-center">
          <div
            class="text-h5 flex-grow-1 py-1 d-flex align-center"
            :style="group.color ? { borderLeft: `4px solid ${group.color}`, paddingLeft: '10px' } : { paddingLeft: '2px' }"
            style="font-weight: normal;"
          >
            <v-icon
              size="small"
              class="mr-2"
              :color="group.color || undefined"
            >
              {{ $globals.icons.tagGroups }}
            </v-icon>
            <NuxtLink
              :to="`/g/${groupSlug}?tagGroups=${group.id}`"
              class="text-decoration-none text-high-emphasis"
            >
              {{ group.name }}
            </NuxtLink>
            <v-chip
              size="x-small"
              variant="tonal"
              class="ml-2"
              :color="group.color || undefined"
            >
              {{ (tagsByGroup[group.id] ?? []).length }}
            </v-chip>
          </div>
          <v-btn
            icon
            variant="text"
            size="small"
            :title="$t('tag.create-a-tag')"
            @click="openCreateTagDialog(group.id)"
          >
            <v-icon>{{ $globals.icons.createAlt }}</v-icon>
          </v-btn>
          <ContextMenu
            :items="[groupPresets.edit, groupPresets.delete]"
            @edit="openUpdateGroupDialog(group)"
            @delete="openDeleteGroupDialog(group)"
          />
        </div>
        <v-divider class="mt-1 mb-3" />
        <v-row v-if="(tagsByGroup[group.id] ?? []).length > 0">
          <v-col
            v-for="tag in tagsByGroup[group.id]"
            :key="tag.id"
            cols="12"
            sm="12"
            md="6"
            lg="4"
            xl="3"
          >
            <v-card
              :class="!group.color ? 'left-border' : ''"
              :style="group.color ? { borderLeft: `5px solid ${group.color}` } : {}"
              hover
              :to="`/g/${groupSlug}?tags=${tag.id}`"
            >
              <v-card-actions>
                <v-icon>{{ $globals.icons.tags }}</v-icon>
                <v-card-title class="py-1 text-truncate flex-shrink-1 flex-grow-1">
                  {{ tag.name }}
                </v-card-title>
                <v-chip
                  v-if="tag.recipeCount"
                  size="x-small"
                  variant="tonal"
                  class="mr-1"
                >
                  {{ tag.recipeCount }}
                </v-chip>
                <ContextMenu
                  :items="[presets.delete, presets.edit]"
                  @delete="openDeleteTagDialog(tag)"
                  @edit="openUpdateTagDialog(tag)"
                />
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
        <div v-else class="text-body-2 text-medium-emphasis pl-3 py-1">
          {{ $t("tag.no-tags-in-group") }}
        </div>
      </section>
    </template>

    <!-- Ungrouped tags section -->
    <section v-if="ungroupedTags.length > 0" class="my-4">
      <div class="d-flex align-center">
        <div class="text-h5 flex-grow-1 py-1 d-flex align-center" style="font-weight: normal; padding-left: 2px;">
          <v-icon size="small" class="mr-2 text-medium-emphasis">
            {{ $globals.icons.tags }}
          </v-icon>
          <span>{{ $t('tag.ungrouped') }}</span>
          <v-chip size="x-small" variant="tonal" class="ml-2">
            {{ ungroupedTags.length }}
          </v-chip>
        </div>
      </div>
      <v-divider class="mt-1 mb-3" />
      <v-row>
        <v-col
          v-for="tag in ungroupedTags"
          :key="tag.id"
          cols="12"
          sm="12"
          md="6"
          lg="4"
          xl="3"
        >
          <v-card
            class="left-border"
            hover
            :to="`/g/${groupSlug}?tags=${tag.id}`"
          >
            <v-card-actions>
              <v-icon>{{ $globals.icons.tags }}</v-icon>
              <v-card-title class="py-1 text-truncate flex-shrink-1 flex-grow-1">
                {{ tag.name }}
              </v-card-title>
              <v-chip
                v-if="tag.recipeCount"
                size="x-small"
                variant="tonal"
                class="mr-1"
              >
                {{ tag.recipeCount }}
              </v-chip>
              <ContextMenu
                :items="[presets.delete, presets.edit]"
                @delete="openDeleteTagDialog(tag)"
                @edit="openUpdateTagDialog(tag)"
              />
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </section>

    <!-- Empty state -->
    <div v-if="visibleGroups.length === 0 && ungroupedTags.length === 0" class="text-center mt-8 text-medium-emphasis">
      {{ $t('search.no-results') }}
    </div>
  </v-container>
</template>

<script setup lang="ts">
import Fuse from "fuse.js";
import { useTagStore, useTagGroupStore } from "~/composables/store";
import { useContextPresets } from "~/composables/use-context-presents";
import { deepCopy } from "~/composables/use-utils";
import { useRouteQuery } from "~/composables/use-router";
import type { TagOut, TagGroupOut } from "~/lib/api/types/recipe";

definePageMeta({
  middleware: ["auth", "group-only"],
});

const i18n = useI18n();
const auth = useMealieAuth();
const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string || auth.user.value?.groupSlug || "");

useSeoMeta({ title: i18n.t("sidebar.tags") });

const { store: tagStore, actions: tagActions } = useTagStore();
const { store: tagGroupStore, actions: tagGroupActions } = useTagGroupStore();
const presets = useContextPresets();

onMounted(() => {
  tagActions.refresh();
  tagGroupActions.refresh();
});

const groupPresets = {
  edit: presets.edit,
  delete: presets.delete,
};

// ============================================================
// Search

const searchString = useRouteQuery("q", "");

const fuseOptions = {
  ignoreLocation: true,
  shouldSort: true,
  threshold: 0.2,
  keys: ["name"],
};

const fuse = computed(() => new Fuse(tagStore.value as TagOut[], fuseOptions));
const groupFuse = computed(() => new Fuse(tagGroupStore.value as TagGroupOut[], fuseOptions));

const matchingGroupIds = computed<Set<string>>(() => {
  const q = searchString.value.trim();
  if (!q) return new Set();
  return new Set(groupFuse.value.search(q).map(r => r.item.id));
});

const filteredTags = computed<TagOut[]>(() => {
  const q = searchString.value.trim();
  if (!q) return tagStore.value as TagOut[];
  const directMatches = new Set(fuse.value.search(q).map(r => r.item.id));
  return (tagStore.value as TagOut[]).filter(
    t => directMatches.has(t.id) || (t.tagGroupId && matchingGroupIds.value.has(t.tagGroupId)),
  );
});

// ============================================================
// Grouping

const sortedGroups = computed<TagGroupOut[]>(() =>
  [...tagGroupStore.value].sort((a, b) => a.position - b.position || a.name.localeCompare(b.name)),
);

const existingGroupIds = computed<Set<string>>(() => new Set(tagGroupStore.value.map(g => g.id)));

const tagsByGroup = computed(() => {
  const result: Record<string, TagOut[]> = {};
  for (const tag of filteredTags.value) {
    const gid = tag.tagGroupId;
    if (gid && existingGroupIds.value.has(gid)) {
      if (!result[gid]) result[gid] = [];
      result[gid].push(tag);
    }
  }
  // Sort tags within each group alphabetically
  for (const gid of Object.keys(result)) {
    result[gid].sort((a, b) => a.name.localeCompare(b.name));
  }
  return result;
});

const ungroupedTags = computed<TagOut[]>(() =>
  filteredTags.value
    .filter(t => !t.tagGroupId || !existingGroupIds.value.has(t.tagGroupId))
    .sort((a, b) => a.name.localeCompare(b.name)),
);

// When no search is active, show all tag groups (even empty ones so newly created groups are visible).
// When searching, show groups that have matching tags or whose group name matches the query.
const visibleGroups = computed(() => {
  const q = searchString.value.trim();
  if (!q) return sortedGroups.value;
  return sortedGroups.value.filter(
    g => (tagsByGroup.value[g.id] ?? []).length > 0 || matchingGroupIds.value.has(g.id),
  );
});

// ============================================================
// Dialogs state

const dialogs = ref({
  createGroup: false,
  updateGroup: false,
  deleteGroup: false,
  createTag: false,
  updateTag: false,
  deleteTag: false,
});

// ============================================================
// Tag Group CRUD

const defaultGroupForm = () => ({ name: "", color: "", position: 0 });
const groupForm = ref(defaultGroupForm());
const updateGroupTarget = ref<TagGroupOut | null>(null);
const deleteGroupTarget = ref<TagGroupOut | null>(null);

function openCreateGroupDialog() {
  groupForm.value = defaultGroupForm();
  dialogs.value.createGroup = true;
}

async function createGroup() {
  if (!groupForm.value.name) return;
  await tagGroupActions.createOne({
    name: groupForm.value.name,
    color: groupForm.value.color || null,
    position: Number(groupForm.value.position) || 0,
  } as TagGroupOut);
  dialogs.value.createGroup = false;
}

function openUpdateGroupDialog(group: TagGroupOut) {
  updateGroupTarget.value = { ...deepCopy(group), color: group.color ?? "" };
  dialogs.value.updateGroup = true;
}

async function updateGroup() {
  if (!updateGroupTarget.value) return;
  await tagGroupActions.updateOne({
    ...updateGroupTarget.value,
    color: updateGroupTarget.value.color || null,
    position: Number(updateGroupTarget.value.position) || 0,
  });
  dialogs.value.updateGroup = false;
  updateGroupTarget.value = null;
}

function openDeleteGroupDialog(group: TagGroupOut) {
  deleteGroupTarget.value = group;
  dialogs.value.deleteGroup = true;
}

async function deleteGroup() {
  if (!deleteGroupTarget.value) return;
  await tagGroupActions.deleteOne(deleteGroupTarget.value.id);
  await tagActions.refresh();
  dialogs.value.deleteGroup = false;
  deleteGroupTarget.value = null;
}

// ============================================================
// Tag CRUD

const defaultTagForm = (tagGroupId: string | null = null) => ({ name: "", tagGroupId });
const tagForm = ref(defaultTagForm());
const updateTagTarget = ref<(TagOut & { tagGroupId?: string | null }) | null>(null);
const deleteTagTarget = ref<TagOut | null>(null);

function openCreateTagDialog(tagGroupId: string | null = null) {
  tagForm.value = defaultTagForm(tagGroupId);
  dialogs.value.createTag = true;
}

async function createTag() {
  if (!tagForm.value.name) return;
  await tagActions.createOne({
    name: tagForm.value.name,
    tagGroupId: tagForm.value.tagGroupId || null,
  } as any);
  dialogs.value.createTag = false;
  tagForm.value = defaultTagForm();
}

function openUpdateTagDialog(tag: TagOut) {
  updateTagTarget.value = deepCopy(tag) as TagOut & { tagGroupId?: string | null };
  dialogs.value.updateTag = true;
}

async function updateTag() {
  if (!updateTagTarget.value) return;
  await tagActions.updateOne({
    ...updateTagTarget.value,
    tagGroupId: updateTagTarget.value.tagGroupId || null,
  } as any);
  dialogs.value.updateTag = false;
  updateTagTarget.value = null;
}

function openDeleteTagDialog(tag: TagOut) {
  deleteTagTarget.value = tag;
  dialogs.value.deleteTag = true;
}

async function deleteTag() {
  if (!deleteTagTarget.value) return;
  await tagActions.deleteOne(deleteTagTarget.value.id);
  dialogs.value.deleteTag = false;
  deleteTagTarget.value = null;
}
</script>
