<template>
  <div>
    <GroupDataPage
      :icon="$globals.icons.tagGroups"
      :title="$t('data-pages.tag-groups.tag-group-data')"
      :create-title="$t('data-pages.tag-groups.new-tag-group')"
      :edit-title="$t('data-pages.tag-groups.edit-tag-group')"
      :table-headers="tableHeaders"
      :table-config="tableConfig"
      :data="tagGroupsWithCounts"
      :bulk-actions="[{ icon: $globals.icons.delete, text: $t('general.delete'), event: 'delete-selected' }]"
      :create-form="createForm"
      :edit-form="editForm"
      @create-one="handleCreate"
      @edit-one="handleEdit"
      @delete-one="handleDeleteOne"
      @bulk-action="handleBulkAction"
    >
      <template #[`item.color`]="{ item }">
        <div v-if="item.color" class="d-flex align-center ga-2">
          <div
            :style="{ backgroundColor: item.color, width: '18px', height: '18px', borderRadius: '50%', flexShrink: 0 }"
          />
          <span>{{ item.color }}</span>
        </div>
        <span v-else class="text-medium-emphasis">—</span>
      </template>

      <template #[`item.tagCount`]="{ item }">
        <NuxtLink v-if="groupSlug && item.tagCount > 0" :to="`/g/${groupSlug}?tagGroups=${item.id}`">
          {{ item.tagCount }}
        </NuxtLink>
        <span v-else>{{ item.tagCount || 0 }}</span>
      </template>
    </GroupDataPage>
  </div>
</template>

<script setup lang="ts">
import { validators } from "~/composables/use-validators";
import { useTagGroupStore, useTagStore } from "~/composables/store";
import { fieldTypes } from "~/composables/forms";
import type { AutoFormItems } from "~/types/auto-forms";
import type { TagGroupOut } from "~/lib/api/types/recipe";
import type { TableHeaders, TableConfig } from "~/components/global/CrudTable.vue";

interface TagGroupWithCount extends TagGroupOut {
  tagCount: number;
}

const i18n = useI18n();
const auth = useMealieAuth();
const groupSlug = computed(() => auth.user.value?.groupSlug || "");

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
    text: i18n.t("tag.tag-group-color"),
    value: "color",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("tag.tag-group-position"),
    value: "position",
    show: true,
    sortable: true,
  },
  {
    text: i18n.t("tag.tag-count"),
    value: "tagCount",
    show: true,
    sortable: true,
  },
];

const tagGroupStore = useTagGroupStore();
const tagStore = useTagStore();

onMounted(() => {
  tagGroupStore.actions.refresh();
  tagStore.actions.refresh();
});

const tagCountsByGroupId = computed(() => {
  const counts: Record<string, number> = {};
  for (const tag of tagStore.store.value || []) {
    if (tag.tagGroupId) {
      counts[tag.tagGroupId] = (counts[tag.tagGroupId] || 0) + 1;
    }
  }
  return counts;
});

const tagGroupsWithCounts = computed<TagGroupWithCount[]>(() =>
  (tagGroupStore.store.value || []).map(group => ({
    ...group,
    tagCount: tagCountsByGroupId.value[group.id] || 0,
  })),
);

// ============================================================
// Form items (shared)
const formItems: AutoFormItems = [
  {
    label: i18n.t("general.name"),
    varName: "name",
    type: fieldTypes.TEXT,
    rules: [validators.required],
  },
  {
    label: i18n.t("tag.tag-group-color"),
    varName: "color",
    type: fieldTypes.COLOR,
  },
  {
    label: i18n.t("tag.tag-group-position"),
    varName: "position",
    type: fieldTypes.NUMBER,
    numberInputConfig: {
      min: 0,
      precision: 0,
      controlVariant: "default",
    },
  },
];

// ============================================================
// Create
const createForm = reactive({
  items: formItems,
  data: { name: "", color: "", position: 0 } as unknown as TagGroupOut,
});

async function handleCreate(createFormData: TagGroupOut) {
  await tagGroupStore.actions.createOne({
    ...createFormData,
    color: createFormData.color || null,
    position: Number(createFormData.position) || 0,
  });
  createForm.data = { name: "", color: "", position: 0 } as unknown as TagGroupOut;
}

// ============================================================
// Edit
const editForm = reactive({
  items: formItems,
  data: {} as TagGroupOut,
});

async function handleEdit(editFormData: TagGroupOut) {
  await tagGroupStore.actions.updateOne({
    ...editFormData,
    color: editFormData.color || null,
    position: Number(editFormData.position) || 0,
  });
  editForm.data = {} as TagGroupOut;
}

// ============================================================
// Delete & Bulk Actions
async function handleDeleteOne(id: string | number) {
  await tagGroupStore.actions.deleteOne(id);
  await tagStore.actions.refresh();
}

async function handleBulkAction(event: string, items: TagGroupOut[]) {
  if (event === "delete-selected") {
    const ids = items.filter(item => item.id != null).map(item => item.id);
    await tagGroupStore.actions.deleteMany(ids);
    await tagStore.actions.refresh();
  }
}
</script>
