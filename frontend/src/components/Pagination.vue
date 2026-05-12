<script setup lang="ts">
import { computed } from "vue";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  EllipsisHorizontalIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";

interface Props {
  currentPage: number;
  totalItems: number;
  pageSize?: number;
  maxVisiblePages?: number;
}

const props = withDefaults(defineProps<Props>(), {
  pageSize: 10,
  maxVisiblePages: 5,
});

const emit = defineEmits<{
  (e: "update:currentPage", page: number): void;
  (e: "update:pageSize", size: number): void;
}>();

const { t } = useI18n();

const totalPages = computed(() => Math.ceil(props.totalItems / props.pageSize));

const startItem = computed(() => {
  if (props.totalItems === 0) return 0;
  return (props.currentPage - 1) * props.pageSize + 1;
});

const endItem = computed(() => {
  const end = props.currentPage * props.pageSize;
  return end > props.totalItems ? props.totalItems : end;
});

const visiblePages = computed(() => {
  const pages: (number | "ellipsis")[] = [];
  const { currentPage, maxVisiblePages } = props;
  const total = totalPages.value;

  if (total <= maxVisiblePages + 2) {
    // 显示所有页码
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    // 始终显示第一页
    pages.push(1);

    if (currentPage > 3) {
      pages.push("ellipsis");
    }

    // 计算中间显示的页码
    let start = Math.max(2, currentPage - 1);
    let end = Math.min(total - 1, currentPage + 1);

    if (currentPage < 3) {
      end = Math.min(total - 1, maxVisiblePages - 1);
    } else if (currentPage > total - 2) {
      start = Math.max(2, total - maxVisiblePages + 2);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (currentPage < total - 2) {
      pages.push("ellipsis");
    }

    // 始终显示最后一页
    if (total > 1) {
      pages.push(total);
    }
  }

  return pages;
});

function goToPage(page: number) {
  if (page >= 1 && page <= totalPages.value && page !== props.currentPage) {
    emit("update:currentPage", page);
  }
}

function prevPage() {
  if (props.currentPage > 1) {
    emit("update:currentPage", props.currentPage - 1);
  }
}

function nextPage() {
  if (props.currentPage < totalPages.value) {
    emit("update:currentPage", props.currentPage + 1);
  }
}

function handlePageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement;
  const newSize = parseInt(target.value, 10);
  emit("update:pageSize", newSize);
  emit("update:currentPage", 1); // 切换每页条数时重置到第一页
}
</script>

<template>
  <div
    v-if="totalItems > 0"
    class="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 bg-card border-t border-border">
    <!-- 显示信息 -->
    <div class="text-sm text-foreground-secondary">
      {{ t("pagination.showing") }}
      <span class="font-medium text-foreground">{{ startItem }}</span>
      {{ t("pagination.to") }}
      <span class="font-medium text-foreground">{{ endItem }}</span>
      {{ t("pagination.of") }}
      <span class="font-medium text-foreground">{{ totalItems }}</span>
      {{ t("pagination.items") }}
    </div>

    <div class="flex items-center gap-4">
      <!-- 每页条数选择 -->
      <div class="flex items-center gap-2">
        <span class="text-sm text-foreground-secondary">{{
          t("pagination.pageSize")
        }}</span>
        <select
          :value="pageSize"
          @change="handlePageSizeChange"
          class="px-2 py-1 text-sm border border-border bg-background text-foreground rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
      </div>

      <!-- 分页按钮 -->
      <nav class="flex items-center gap-1" aria-label="Pagination">
        <!-- 上一页按钮 -->
        <button
          @click="prevPage"
          :disabled="currentPage === 1"
          :class="[
            'p-2 rounded-lg transition-colors',
            currentPage === 1
              ? 'text-slate-300 cursor-not-allowed'
              : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
          ]">
          <ChevronLeftIcon class="w-5 h-5" />
        </button>

        <!-- 页码按钮 -->
        <template v-for="(page, index) in visiblePages" :key="index">
          <span v-if="page === 'ellipsis'" class="px-2 text-slate-400">
            <EllipsisHorizontalIcon class="w-5 h-5" />
          </span>
          <button
            v-else
            @click="goToPage(page)"
            :class="[
              'min-w-[36px] h-9 px-3 text-sm font-medium rounded-lg transition-colors',
              page === currentPage
                ? 'bg-indigo-600 text-white'
                : 'text-foreground hover:bg-hover',
            ]">
            {{ page }}
          </button>
        </template>

        <!-- 下一页按钮 -->
        <button
          @click="nextPage"
          :disabled="currentPage === totalPages"
          :class="[
            'p-2 rounded-lg transition-colors',
            currentPage === totalPages
              ? 'text-slate-300 cursor-not-allowed'
              : 'text-foreground-secondary hover:bg-hover hover:text-foreground',
          ]">
          <ChevronRightIcon class="w-5 h-5" />
        </button>
      </nav>
    </div>
  </div>
</template>
