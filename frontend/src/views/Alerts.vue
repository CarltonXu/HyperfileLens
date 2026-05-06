<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// TODO: 实现监控告警功能
</script>

<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-slate-900 dark:text-white">{{ t('nav.alerts') }}</h1>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          系统告警和监控规则配置
        </p>
      </div>
    </div>

    <!-- 占位内容 -->
    <div class="bg-white dark:bg-slate-800 rounded-lg shadow p-12 text-center">
      <div class="text-slate-400 dark:text-slate-500">
        <svg class="w-16 h-16 mx-auto mb-4 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 class="text-lg font-medium text-slate-600 dark:text-slate-300 mb-2">功能开发中</h3>
        <p class="text-sm">监控告警功能正在开发中，敬请期待</p>
      </div>
    </div>
  </div>
</template>
