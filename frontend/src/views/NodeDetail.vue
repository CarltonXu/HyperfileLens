<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const { t } = useI18n()
const route = useRoute()
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-900">{{ t('nav.nodeDetails') }}</h1>
    <p class="text-gray-500">Node ID: {{ route.params.id }}</p>
  </div>
</template>
