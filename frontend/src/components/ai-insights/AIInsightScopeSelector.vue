<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  CircleStackIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  ServerStackIcon,
  Square3Stack3DIcon,
} from "@heroicons/vue/24/outline";
import { aiInsightsApi, type AIInsightScopeOption } from "@/api";

const route = useRoute();
const router = useRouter();

type ScopeType = "tenant" | "repository" | "backup_task" | "snapshot";

const scopeTypes: Array<{
  key: ScopeType;
  label: string;
  icon: typeof CircleStackIcon;
}> = [
  { key: "tenant", label: "Tenant", icon: Square3Stack3DIcon },
  { key: "repository", label: "Repository", icon: CircleStackIcon },
  { key: "backup_task", label: "Backup Task", icon: ServerStackIcon },
  { key: "snapshot", label: "Snapshot", icon: FolderIcon },
];

const loading = ref(false);
const options = ref<AIInsightScopeOption[]>([]);
const search = ref("");
const loadError = ref("");

const currentScopeType = computed<ScopeType>(() => {
  const value = String(route.query.scope_type || "tenant");
  return scopeTypes.some((item) => item.key === value)
    ? (value as ScopeType)
    : "tenant";
});

const currentScopeId = computed(() => String(route.query.scope_id || ""));
const selectedOption = computed(() =>
  options.value.find((item) => item.id === currentScopeId.value),
);

const scopeLabel = computed(() => {
  if (currentScopeType.value === "tenant") return "All indexed tenant data";
  return (
    selectedOption.value?.name ||
    String(route.query.scope_name || "") ||
    "Select a data source"
  );
});

function formatCount(value: number) {
  return Number(value || 0).toLocaleString();
}

function formatBytes(bytes: number) {
  const value = Number(bytes || 0);
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function optionMeta(option: AIInsightScopeOption) {
  const parts = [
    `${formatCount(option.indexed_snapshots)} snapshots`,
    `${formatCount(option.indexed_files)} files`,
    formatBytes(option.total_size),
  ];
  if (option.repository_name && currentScopeType.value !== "repository") {
    parts.push(option.repository_name);
  }
  if (option.task_name && currentScopeType.value === "snapshot") {
    parts.push(option.task_name);
  }
  return parts.join(" · ");
}

async function loadOptions() {
  loadError.value = "";
  if (currentScopeType.value === "tenant") {
    options.value = [];
    return;
  }

  loading.value = true;
  try {
    const response = await aiInsightsApi.scopeOptions({
      scope_type: currentScopeType.value,
      search: search.value.trim() || undefined,
      limit: 100,
    });
    options.value = response.data?.results || [];
  } catch (error) {
    console.error("Failed to load AI Insights scopes:", error);
    options.value = [];
    loadError.value = "Failed to load available data sources.";
  } finally {
    loading.value = false;
  }
}

function applyScope(scopeType: ScopeType, option?: AIInsightScopeOption) {
  const query = { ...route.query };
  query.scope_type = scopeType;

  if (scopeType === "tenant") {
    delete query.scope_id;
    delete query.scope_name;
  } else if (option) {
    query.scope_id = option.id;
    query.scope_name = option.name;
  } else {
    delete query.scope_id;
    delete query.scope_name;
  }

  router.push({ path: route.path, query });
}

function changeScopeType(scopeType: ScopeType) {
  search.value = "";
  applyScope(scopeType);
}

function changeOption(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  const option = options.value.find((item) => item.id === value);
  if (option) {
    applyScope(currentScopeType.value, option);
  }
}

let searchTimer: number | undefined;
watch(search, () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    loadOptions();
  }, 250);
});

watch(
  () => currentScopeType.value,
  () => {
    loadOptions();
  },
);

onMounted(() => {
  loadOptions();
});
</script>

<template>
  <div class="rounded-lg border border-border bg-card p-4">
    <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div class="min-w-0">
        <div class="text-xs font-medium uppercase tracking-wide text-foreground-muted">
          Analysis source
        </div>
        <div class="mt-1 truncate text-sm font-semibold text-foreground">
          {{ scopeLabel }}
        </div>
      </div>

      <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div class="grid grid-cols-2 gap-1 rounded-lg border border-border bg-background-secondary p-1 sm:flex">
          <button
            v-for="item in scopeTypes"
            :key="item.key"
            type="button"
            :class="[
              'inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 text-xs font-medium transition-colors',
              currentScopeType === item.key
                ? 'bg-card text-foreground shadow-sm'
                : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
            ]"
            @click="changeScopeType(item.key)"
          >
            <component :is="item.icon" class="h-4 w-4" />
            <span>{{ item.label }}</span>
          </button>
        </div>

        <div
          v-if="currentScopeType !== 'tenant'"
          class="flex min-w-0 flex-col gap-2 sm:min-w-[440px] sm:flex-row"
        >
          <label class="relative min-w-0 flex-1">
            <MagnifyingGlassIcon
              class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted"
            />
            <input
              v-model="search"
              type="search"
              placeholder="Filter sources"
              class="h-10 w-full rounded-lg border border-border bg-background-secondary pl-9 pr-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>

          <select
            :value="currentScopeId"
            class="h-10 min-w-0 rounded-lg border border-border bg-background-secondary px-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 sm:w-[260px]"
            :disabled="loading || options.length === 0"
            @change="changeOption"
          >
            <option value="">
              {{ loading ? "Loading sources..." : "Choose source" }}
            </option>
            <option
              v-for="option in options"
              :key="option.id"
              :value="option.id"
            >
              {{ option.name }} · {{ formatCount(option.indexed_files) }} files
            </option>
          </select>
        </div>
      </div>
    </div>

    <div
      v-if="currentScopeType !== 'tenant'"
      class="mt-3 flex flex-wrap items-center gap-2 text-xs text-foreground-muted"
    >
      <span v-if="loading">Loading available data sources...</span>
      <span v-else-if="loadError" class="text-red-600 dark:text-red-400">
        {{ loadError }}
      </span>
      <span v-else-if="selectedOption">
        {{ optionMeta(selectedOption) }}
      </span>
      <span v-else-if="options.length === 0">
        No indexed sources found for this scope.
      </span>
      <span v-else>
        Select one source to bind all charts, search, and AI chat to the same data range.
      </span>
    </div>
  </div>
</template>
