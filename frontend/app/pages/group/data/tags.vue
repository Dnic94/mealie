<template>
  <div>
    <!-- Merge Dialog -->
    <BaseDialog
      v-model="mergeDialog"
      bottom-sheet
      :icon="$globals.icons.tags"
      :title="$t('data-pages.tags.combine-tag')"
      can-confirm
      @confirm="mergeTags"
      @close="resetMergeDialog"
    >
      <v-card-text>
        <div>
          {{ $t("data-pages.tags.merge-dialog-text") }}
        </div>
        <v-autocomplete
          v-model="fromTag"
          return-object
          :items="tagStore.store.value"
          :custom-filter="normalizeFilter"
          item-title="name"
          :label="$t('data-pages.tags.source-tag')"
        />
        <v-autocomplete
          v-model="toTag"
          return-object
          :items="tagStore.store.value"
          :custom-filter="normalizeFilter"
          item-title="name"
          :label="$t('data-pages.tags.target-tag')"
        />

        <template v-if="canMerge && fromTag && toTag">
          <div class="text-center">
            {{ $t("data-pages.tags.merge-tag-example", { tag1: fromTag.name, tag2: toTag.name }) }}
          </div>
        </template>
      </v-card-text>
    </BaseDialog>

    <!-- Delete Unused Dialog -->
    <BaseDialog
      v-model="deleteUnusedDialog"
      bottom-sheet
      :title="$t('general.confirm')"
      :icon="$globals.icons.alertCircle"
      color="error"
      can-confirm
      @confirm="confirmDeleteUnused"
    >
      <v-card-text>
        {{ $t('data-pages.tags.delete-unused-confirm', { count: unusedTagIds.length }, unusedTagIds.length) }}
        <ul style="margin: 0.5rem 0 0; padding-left: 1.25rem; font-size: 0.85rem; color: rgba(var(--v-theme-on-surface), 0.7); line-height: 1.8;">
          <li v-for="name in unusedTagNamesPreview" :key="name">
            {{ name }}
          </li>
        </ul>
        <div v-if="unusedTagNamesRemaining > 0" class="text-body-2 pl-2">
          {{ $t('data-pages.delete-unused-more', { count: unusedTagNamesRemaining }) }}
        </div>
      </v-card-text>
    </BaseDialog>

    <!-- Bulk Assign Tag Group Dialog -->
    <BaseDialog
      v-model="bulkAssignGroupDialog"
      bottom-sheet
      :title="$t('data-pages.tags.assign-tag-group')"
      :icon="$globals.icons.tagGroups"
      can-confirm
      @confirm="assignSelected"
    >
      <v-card-text>
        <v-card class="mb-4">
          <v-card-title>{{ $t("general.caution") }}</v-card-title>
          <v-card-text>{{ $t("data-pages.tags.tag-group-overwrite-warning") }}</v-card-text>
        </v-card>

        <v-autocomplete
          v-model="bulkAssignGroupId"
          clearable
          :items="sortedTagGroups"
          :custom-filter="normalizeFilter"
          item-value="id"
          item-title="name"
          :prepend-inner-icon="$globals.icons.tagGroups"
          :label="$t('tag.tag-group')"
          :placeholder="$t('tag.ungrouped')"
          persistent-placeholder
        />
        <v-card variant="outlined">
          <v-virtual-scroll height="300" item-height="28" :items="bulkAssignTarget">
            <template #default="{ item }">
              <v-list-item class="pb-2">
                <v-list-item-title>{{ item.name }}</v-list-item-title>
              </v-list-item>
            </template>
          </v-virtual-scroll>
        </v-card>
      </v-card-text>
    </BaseDialog>

    <GroupDataPage
      :icon="$globals.icons.tags"
      :title="$t('data-pages.tags.tag-data')"
      :create-title="$t('data-pages.tags.new-tag')"
      :edit-title="$t('data-pages.tags.edit-tag')"
      :table-headers="tableHeaders"
      :table-config="tableConfig"
      :data="tagStore.store.value || []"
      :bulk-actions="[
        { icon: $globals.icons.delete, text: $t('general.delete'), event: 'delete-selected' },
        { icon: $globals.icons.tagGroups, text: $t('data-pages.tags.assign-tag-group'), event: 'assign-selected' },
      ]"
      :create-form="createForm"
      :edit-form="editForm"
      @create-one="handleCreate"
      @edit-one="handleEdit"
      @delete-one="tagStore.actions.deleteOne"
      @bulk-action="handleBulkAction"
    >
      <template #[`item.tagGroupId`]="{ item }">
        <v-chip
          v-if="item.tagGroupId && tagGroupById[item.tagGroupId]"
          size="small"
          label
          variant="flat"
          :color="tagGroupById[item.tagGroupId]?.color || 'accent'"
          :to="groupSlug ? `/g/${groupSlug}?tagGroups=${item.tagGroupId}` : undefined"
        >
          {{ tagGroupById[item.tagGroupId]?.name }}
        </v-chip>
        <span v-else class="text-medium-emphasis">—</span>
      </template>

      <template #[`item.recipeCount`]="{ item }">
        <NuxtLink v-if="groupSlug && item.recipeCount > 0" :to="`/g/${groupSlug}?tags=${item.id}`">{{ item.recipeCount }}</NuxtLink>
        <span v-else>{{ item.recipeCount || 0 }}</span>
      </template>

      <template #table-button-row>
        <BaseButton @click="mergeDialog = true">
          <template #icon>
            {{ $globals.icons.externalLink }}
          </template>
          {{ $t("data-pages.combine") }}
        </BaseButton>

        <v-divider vertical class="mx-2" />

        <BaseButton color="error" :loading="loadingEmpty" @click="openDeleteUnusedDialog">
          <template #icon>
            {{ $globals.icons.broom }}
          </template>
          {{ $t("data-pages.delete-unused") }}
        </BaseButton>
      </template>
    </GroupDataPage>
  </div>
</template>

<script setup lang="ts">
import { validators } from "~/composables/use-validators";
import { useTagStore, useTagGroupStore } from "~/composables/store";
import { useUserApi } from "~/composables/api";
import { fieldTypes } from "~/composables/forms";
import { normalizeFilter } from "~/composables/use-utils";
import { alert } from "~/composables/use-toast";
import type { AutoFormItems } from "~/types/auto-forms";
import type { RecipeTag, TagGroupOut } from "~/lib/api/types/recipe";
import type { TableHeaders, TableConfig } from "~/components/global/CrudTable.vue";

const i18n = useI18n();
const auth = useMealieAuth();
const groupSlug = computed(() => auth.user.value?.groupSlug || "");
const userApi = useUserApi();

const tagStore = useTagStore();
const tagGroupStore = useTagGroupStore();

const sortedTagGroups = computed<TagGroupOut[]>(() =>
  [...(tagGroupStore.store.value || [])].sort(
    (a, b) => a.position - b.position || a.name.localeCompare(b.name),
  ),
);

const tagGroupById = computed<Record<string, TagGroupOut>>(() => {
  const map: Record<string, TagGroupOut> = {};
  for (const group of tagGroupStore.store.value || []) {
    map[group.id] = group;
  }
  return map;
});

const tagGroupOptions = computed(() => [
  { text: `— ${i18n.t("tag.ungrouped")} —`, value: "" },
  ...sortedTagGroups.value.map(group => ({ text: group.name, value: group.id })),
]);

const tableConfig: TableConfig = {
  hideColumns: true,
  canExport: true,
};
const tableHeaders: TableHeaders[] = [
  {
    text: i18n.t("general.id"),
    value: "id",
    show: false,
  },
  {
    text: i18n.t("general.name"),
    value: "name",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("tag.tag-group"),
    value: "tagGroupId",
    show: true,
    sortable: true,
    sort: (gid1: string | null | undefined, gid2: string | null | undefined) => {
      const name1 = (gid1 && tagGroupById.value[gid1]?.name) || "";
      const name2 = (gid2 && tagGroupById.value[gid2]?.name) || "";
      return name1.localeCompare(name2);
    },
  },
  {
    text: i18n.t("data-pages.recipe-count"),
    value: "recipeCount",
    show: true,
    sortable: true,
  },
];

onMounted(() => {
  tagStore.actions.refresh();
  tagGroupStore.actions.refresh();
});

// ============================================================
// Form items (shared)
const formItems = computed<AutoFormItems>(() => [
  {
    label: i18n.t("general.name"),
    varName: "name",
    type: fieldTypes.TEXT,
    rules: [validators.required],
  },
  {
    label: i18n.t("tag.tag-group"),
    varName: "tagGroupId",
    type: fieldTypes.SELECT,
    options: tagGroupOptions.value,
    selectReturnValue: "value",
  },
]);

// ============================================================
// Create
const createForm = reactive({
  get items() {
    return formItems.value;
  },
  data: { name: "", tagGroupId: null } as RecipeTag,
});

async function handleCreate(createFormData: RecipeTag) {
  await tagStore.actions.createOne({
    ...createFormData,
    tagGroupId: createFormData.tagGroupId || null,
  });
  createForm.data = { name: "", tagGroupId: null } as RecipeTag;
}

// ============================================================
// Edit
const editForm = reactive({
  get items() {
    return formItems.value;
  },
  data: {} as RecipeTag,
});

async function handleEdit(editFormData: RecipeTag) {
  await tagStore.actions.updateOne({
    ...editFormData,
    tagGroupId: editFormData.tagGroupId || null,
  });
  editForm.data = {} as RecipeTag;
}

// ============================================================
// Bulk Actions
async function handleBulkAction(event: string, items: RecipeTag[]) {
  if (event === "delete-selected") {
    const ids = items.filter(item => item.id != null).map(item => item.id!);
    await tagStore.actions.deleteMany(ids);
  }
  else if (event === "assign-selected") {
    bulkAssignEventHandler(items);
  }
}

// ============================================================
// Bulk Assign Tag Group
const bulkAssignGroupDialog = ref(false);
const bulkAssignTarget = ref<RecipeTag[]>([]);
const bulkAssignGroupId = ref<string | null>(null);

function bulkAssignEventHandler(selection: RecipeTag[]) {
  bulkAssignTarget.value = selection;
  bulkAssignGroupId.value = null;
  bulkAssignGroupDialog.value = true;
}

async function assignSelected() {
  for (const item of bulkAssignTarget.value) {
    await tagStore.actions.updateOne({
      ...item,
      tagGroupId: bulkAssignGroupId.value || null,
    });
  }
  bulkAssignTarget.value = [];
  bulkAssignGroupId.value = null;
  await tagStore.actions.refresh();
}

// ============================================================
// Merge Tags
const mergeDialog = ref(false);
const fromTag = ref<RecipeTag | null>(null);
const toTag = ref<RecipeTag | null>(null);

const canMerge = computed(() => {
  return fromTag.value && toTag.value && fromTag.value.id !== toTag.value.id;
});

function resetMergeDialog() {
  fromTag.value = null;
  toTag.value = null;
}

async function mergeTags() {
  if (!canMerge.value || !fromTag.value?.id || !toTag.value?.id) {
    return;
  }

  const { data } = await userApi.tags.merge(fromTag.value.id, toTag.value.id);

  if (data) {
    fromTag.value = null;
    toTag.value = null;
    tagStore.actions.refresh();
  }
}

// ============================================================
// Delete Unused
const DELETE_UNUSED_PREVIEW_LIMIT = 10;

const deleteUnusedDialog = ref(false);
const unusedTags = ref<RecipeTag[]>([]);
const unusedTagIds = computed(() => unusedTags.value.filter(t => t.id != null).map(t => t.id!));
const unusedTagNamesPreview = computed(() => unusedTags.value.slice(0, DELETE_UNUSED_PREVIEW_LIMIT).map(t => t.name));
const unusedTagNamesRemaining = computed(() => Math.max(unusedTags.value.length - DELETE_UNUSED_PREVIEW_LIMIT, 0));
const loadingEmpty = ref(false);

async function openDeleteUnusedDialog() {
  loadingEmpty.value = true;
  const { data } = await userApi.tags.getEmpty();
  loadingEmpty.value = false;
  unusedTags.value = data ?? [];

  if (unusedTags.value.length === 0) {
    alert.info(i18n.t("data-pages.tags.no-unused-tags"));
    return;
  }

  deleteUnusedDialog.value = true;
}

async function confirmDeleteUnused() {
  await tagStore.actions.deleteMany(unusedTagIds.value);
  unusedTags.value = [];
}
</script>
