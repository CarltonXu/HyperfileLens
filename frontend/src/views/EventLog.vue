<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// TODO: 实现事件日志功能
</script>

<template>
 <div class="space-y-6">
 <!-- 页面标题 -->
 <div class="flex items-center justify-between">
 <div>
 <h1 class="text-2xl font-semibold text-foreground">{{ t('nav.eventLog') }}</h1>
 <p class="mt-1 text-sm text-foreground-secondary">
 系统事件和告警通知日志
 </p>
 </div>
 </div>

 <!-- 占位内容 -->
 <div class="bg-card rounded-lg shadow p-12 text-center">
 <div class="text-foreground-muted">
 <svg class="w-16 h-16 mx-auto mb-4 text-foreground-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
 </svg>
 <h3 class="text-lg font-medium text-foreground-secondary mb-2">功能开发中</h3>
 <p class="text-sm">事件日志功能正在开发中，敬请期待</p>
 </div>
 </div>
 </div>
</template>
