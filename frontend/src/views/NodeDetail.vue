<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import PageTitle from "@/components/PageTitle.vue";
import { ServerIcon } from "@heroicons/vue/24/outline";

const { t } = useI18n();
const route = useRoute();
</script>

<template>
  <div class="space-y-6">
    <PageTitle
      :icon="ServerIcon"
      :title="t('nav.nodeDetails')"
      :subtitle="`Node ID: ${route.params.id}`"
      icon-class="text-indigo-600 dark:text-indigo-400"
    />
  </div>
</template>
