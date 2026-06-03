<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  EnvelopeIcon,
  MagnifyingGlassIcon,
  PlusIcon,
} from "@heroicons/vue/24/outline";

defineProps<{
  searchQuery: string;
  roleFilter: string;
  statusFilter: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  "update:searchQuery": [value: string];
  "update:roleFilter": [value: string];
  "update:statusFilter": [value: string];
  search: [];
  filter: [];
  refresh: [];
  invite: [];
  create: [];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="sm:flex sm:items-center sm:justify-between">
    <div>
      <h1 class="text-2xl font-semibold text-foreground">
        {{ t("users.title") }}
      </h1>
      <p class="mt-2 text-sm text-foreground-secondary">
        {{ t("users.description") }}
      </p>
    </div>
    <div class="mt-4 sm:mt-0 flex gap-3">
      <button
        type="button"
        class="inline-flex items-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover transition-colors"
        @click="emit('invite')"
      >
        <EnvelopeIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
        {{ t("users.inviteUser") }}
      </button>
      <button
        type="button"
        class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        @click="emit('create')"
      >
        <PlusIcon class="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
        {{ t("users.createUser") }}
      </button>
    </div>
  </div>

  <div class="bg-card shadow rounded-xl border border-border p-4">
    <div class="flex flex-wrap gap-4">
      <div class="flex-1 min-w-0">
        <div class="relative">
          <MagnifyingGlassIcon
            class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
          />
          <input
            :value="searchQuery"
            type="text"
            :placeholder="t('common.search')"
            class="block w-full rounded-lg border border-border py-2 pl-10 pr-3 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
            @input="
              emit(
                'update:searchQuery',
                ($event.target as HTMLInputElement).value,
              );
              emit('search');
            "
          />
        </div>
      </div>
      <div class="flex items-center gap-2">
        <select
          :value="roleFilter"
          class="rounded-lg border border-border py-2 pl-3 pr-8 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
          @change="
            emit(
              'update:roleFilter',
              ($event.target as HTMLSelectElement).value,
            );
            emit('filter');
          "
        >
          <option class="bg-background" value="">
            {{ t("common.all") }}
          </option>
          <option class="bg-background" value="admin">
            {{ t("users.roles.admin") }}
          </option>
          <option class="bg-background" value="member">
            {{ t("users.roles.member") }}
          </option>
        </select>
        <select
          :value="statusFilter"
          class="rounded-lg border border-border py-2 pl-3 pr-8 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
          @change="
            emit(
              'update:statusFilter',
              ($event.target as HTMLSelectElement).value,
            );
            emit('filter');
          "
        >
          <option class="bg-background" value="">
            {{ t("common.all") }}
          </option>
          <option class="bg-background" value="active">
            {{ t("users.active") }}
          </option>
          <option class="bg-background" value="inactive">
            {{ t("users.inactive") }}
          </option>
        </select>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-hover"
          @click="emit('refresh')"
        >
          <ArrowPathIcon
            :class="['h-4 w-4', loading ? 'animate-spin' : '']"
            aria-hidden="true"
          />
          {{ t("common.refresh") }}
        </button>
      </div>
    </div>
  </div>
</template>
