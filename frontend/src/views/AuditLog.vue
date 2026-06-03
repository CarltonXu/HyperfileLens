<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex-shrink-0">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-2xl font-semibold text-foreground">
            {{ t("auditLog.title") }}
          </h1>
          <p class="mt-1 text-sm text-foreground-secondary">
            {{ t("auditLog.description") }}
          </p>
        </div>
        <div class="flex gap-2">
          <button
            @click="exportLogs('json')"
            class="inline-flex items-center px-3 py-2 border border-border rounded-lg text-sm font-medium text-foreground-secondary bg-background hover:bg-hover transition-colors"
          >
            <ArrowDownTrayIcon class="h-4 w-4 mr-2" />
            {{ t("auditLog.export") }}
          </button>
        </div>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div v-if="statistics" class="flex-shrink-0">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          v-for="card in statCards"
          :key="card.label"
          class="bg-card rounded-xl border border-border p-4"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-lg bg-background-secondary flex items-center justify-center"
            >
              <component
                :is="card.icon"
                class="w-5 h-5"
                :class="card.className"
              />
            </div>
            <div>
              <p class="text-xs text-foreground-secondary">{{ card.label }}</p>
              <p :class="['mt-1 text-2xl font-semibold', card.className]">
                {{ card.value }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Logs Table -->
    <div
      class="flex max-h-[calc(100vh-19rem)] min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card"
    >
      <!-- Search & Filters Bar - Compact Design -->
      <div
        class="p-4 border-b border-border flex flex-wrap items-center justify-between gap-3"
      >
        <div class="flex flex-wrap items-center gap-2 flex-1">
          <!-- Search Input with Type Selector -->
          <div
            class="flex-1 min-w-[280px] flex rounded-lg overflow-hidden border border-border"
          >
            <!-- Search Type Dropdown -->
            <div class="relative">
              <button
                @click="showSearchTypeMenu = !showSearchTypeMenu"
                class="h-9 px-3 bg-background-secondary border-r border-border text-sm text-foreground-secondary hover:bg-hover-secondary flex items-center gap-1.5 whitespace-nowrap"
              >
                <span>{{ searchTypeLabel }}</span>
                <ChevronDownIcon class="w-4 h-4" />
              </button>
              <Transition name="dropdown">
                <div
                  v-if="showSearchTypeMenu"
                  class="absolute left-0 top-full mt-1 popover-surface rounded-lg shadow-lg border border-border z-20 min-w-[120px]"
                >
                  <button
                    v-for="type in searchTypes"
                    :key="type.value"
                    @click="selectSearchType(type.value)"
                    :class="[
                      'w-full px-3 py-2 text-left text-sm hover:bg-hover first:rounded-t-lg last:rounded-b-lg',
                      searchType === type.value
                        ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                        : 'text-foreground-secondary',
                    ]"
                  >
                    {{ type.label }}
                  </button>
                </div>
              </Transition>
            </div>
            <!-- Search Input -->
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="searchPlaceholder"
              class="flex-1 h-9 px-3 bg-card text-sm text-foreground placeholder-slate-400 focus:outline-none"
              @keyup.enter="handleSearch"
            />
            <button
              @click="handleSearch"
              class="h-9 px-3 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium flex items-center"
            >
              <MagnifyingGlassIcon class="w-4 h-4" />
            </button>
          </div>

          <!-- Quick Date Filters -->
          <div class="flex items-center gap-1">
            <button
              v-for="preset in datePresets"
              :key="preset.value"
              @click="selectDatePreset(preset.value)"
              :class="[
                'h-9 px-3 rounded-lg text-sm font-medium transition-colors',
                datePreset === preset.value
                  ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                  : 'bg-background-secondary text-foreground-secondary hover:bg-hover-secondary border border-transparent',
              ]"
            >
              {{ preset.label }}
            </button>
          </div>

          <!-- Action Filter -->
          <div class="relative">
            <button
              @click="showActionMenu = !showActionMenu"
              :class="[
                'h-9 px-3 rounded-lg text-sm font-medium border flex items-center gap-1.5',
                filters.action
                  ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800'
                  : 'bg-background text-foreground-secondary border-border hover:bg-hover',
              ]"
            >
              <FunnelIcon class="w-4 h-4" />
              <span>{{
                filters.action
                  ? t(`auditLog.actions.${filters.action}`)
                  : t("auditLog.action")
              }}</span>
              <ChevronDownIcon class="w-4 h-4" />
            </button>
            <Transition name="dropdown">
              <div
                v-if="showActionMenu"
                class="absolute right-0 top-full mt-1 popover-surface rounded-lg shadow-lg border border-border z-20 min-w-[140px]"
              >
                <button
                  @click="selectAction('')"
                  :class="[
                    'w-full px-3 py-2 text-left text-sm hover:bg-hover first:rounded-t-lg',
                    !filters.action
                      ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                      : 'text-foreground-secondary',
                  ]"
                >
                  {{ t("common.all") }}
                </button>
                <button
                  v-for="action in actionOptions"
                  :key="action"
                  @click="selectAction(action)"
                  :class="[
                    'w-full px-3 py-2 text-left text-sm hover:bg-hover last:rounded-b-lg',
                    filters.action === action
                      ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                      : 'text-foreground-secondary',
                  ]"
                >
                  {{ t(`auditLog.actions.${action}`) }}
                </button>
              </div>
            </Transition>
          </div>

          <!-- Resource Type Filter -->
          <div class="relative">
            <button
              @click="showResourceMenu = !showResourceMenu"
              :class="[
                'h-9 px-3 rounded-lg text-sm font-medium border flex items-center gap-1.5',
                filters.resource_type
                  ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800'
                  : 'bg-background text-foreground-secondary border-border hover:bg-hover',
              ]"
            >
              <CubeIcon class="w-4 h-4" />
              <span>{{
                filters.resource_type
                  ? t(`auditLog.resourceTypes.${filters.resource_type}`)
                  : t("auditLog.resourceType")
              }}</span>
              <ChevronDownIcon class="w-4 h-4" />
            </button>
            <Transition name="dropdown">
              <div
                v-if="showResourceMenu"
                class="absolute right-0 top-full mt-1 popover-surface rounded-lg shadow-lg border border-border z-20 min-w-[140px]"
              >
                <button
                  @click="selectResourceType('')"
                  :class="[
                    'w-full px-3 py-2 text-left text-sm hover:bg-hover first:rounded-t-lg',
                    !filters.resource_type
                      ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                      : 'text-foreground-secondary',
                  ]"
                >
                  {{ t("common.all") }}
                </button>
                <button
                  v-for="type in resourceTypeOptions"
                  :key="type"
                  @click="selectResourceType(type)"
                  :class="[
                    'w-full px-3 py-2 text-left text-sm hover:bg-hover last:rounded-b-lg',
                    filters.resource_type === type
                      ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                      : 'text-foreground-secondary',
                  ]"
                >
                  {{ t(`auditLog.resourceTypes.${type}`) }}
                </button>
              </div>
            </Transition>
          </div>

          <button
            @click="refreshAuditLogs"
            class="h-9 px-3 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-hover flex items-center gap-1.5"
          >
            <ArrowPathIcon :class="['w-4 h-4', loading ? 'animate-spin' : '']" />
            {{ t("common.refresh") }}
          </button>

          <!-- Reset Filters -->
          <button
            v-if="hasActiveFilters"
            @click="resetFilters"
            class="h-9 px-3 rounded-lg text-sm font-medium text-foreground-secondary hover:text-slate-700 dark:hover:text-slate-200 hover:bg-hover flex items-center gap-1.5"
          >
            <XMarkIcon class="w-4 h-4" />
            {{ t("common.reset") }}
          </button>
        </div>

        <!-- Custom Date Range (when custom is selected) -->
        <Transition name="fade">
          <div
            v-if="datePreset === 'custom'"
            class="mt-3 pt-3 border-t border-border flex items-center gap-3"
          >
            <div class="flex items-center gap-2">
              <label class="text-sm text-foreground-secondary">{{
                t("auditLog.startDate")
              }}</label>
              <input
                v-model="filters.start_date"
                type="date"
                class="h-8 px-2 rounded border border-border bg-background text-sm text-foreground"
              />
            </div>
            <div class="flex items-center gap-2">
              <label class="text-sm text-foreground-secondary">{{
                t("auditLog.endDate")
              }}</label>
              <input
                v-model="filters.end_date"
                type="date"
                class="h-8 px-2 rounded border border-border bg-background text-sm text-foreground"
              />
            </div>
            <button
              @click="applyCustomDate"
              class="h-8 px-3 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium"
            >
              {{ t("common.apply") }}
            </button>
          </div>
        </Transition>
      </div>

      <!-- Single Table with Sticky Header -->
      <div class="relative min-h-0 flex-1 overflow-auto bg-card">
        <table
          class="w-full table-fixed border-separate border-spacing-0"
          :style="{ minWidth: auditLogTable.tableMinWidth.value }"
        >
          <colgroup>
            <col
              v-for="col in columns"
              :key="col.key"
              :style="auditLogTable.columnStyle(col.key)"
            />
          </colgroup>
          <thead class="sticky top-0 z-30 bg-background-secondary shadow-sm">
            <tr>
              <ResizableSortableTh
                v-for="col in columns"
                :key="col.key"
                :column-key="col.key"
                :label="col.label"
                :style-value="auditLogTable.columnStyle(col.key)"
                :sortable="col.sortable !== false"
                :active="auditLogTable.sort.value.key === col.key"
                :align="col.align"
                :sort-icon="auditLogTable.getSortIcon(col.key)"
                :resizing="auditLogTable.resizingColumn.value === col.key"
                header-class="border-b border-border"
                @sort="auditLogTable.toggleSort($event as AuditLogColumnKey)"
                @resize-start="
                  (key, event) =>
                    auditLogTable.startResize(key as AuditLogColumnKey, event)
                "
                @resize-reset="
                  auditLogTable.resetColumnWidth($event as AuditLogColumnKey)
                "
              />
            </tr>
          </thead>
          <tbody class="[&>tr>td]:border-b [&>tr>td]:border-border">
            <tr v-if="loading">
              <td :colspan="columns.length" class="px-4 py-12 text-center">
                <div class="flex flex-col items-center">
                  <div
                    class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"
                  ></div>
                  <span class="mt-2 text-sm text-foreground-secondary">{{
                    t("common.loading")
                  }}</span>
                </div>
              </td>
            </tr>
            <tr v-else-if="logs.length === 0">
              <td :colspan="columns.length" class="px-4 py-12 text-center">
                <div class="flex flex-col items-center">
                  <ClipboardDocumentListIcon
                    class="w-12 h-12 text-foreground-muted"
                  />
                  <span class="mt-2 text-sm text-foreground-secondary">{{
                    t("common.noData")
                  }}</span>
                </div>
              </td>
            </tr>
            <tr
              v-for="log in auditLogTable.sortedRows.value"
              :key="log.id"
              class="hover:bg-hover transition-colors"
            >
                <td
                  class="px-4 py-3 whitespace-nowrap text-center"
                  :style="auditLogTable.columnStyle('timestamp')"
                >
                  <span class="text-sm text-foreground">
                    {{ formatDateTime(log.timestamp) }}
                  </span>
                </td>
                <td
                  class="px-4 py-3"
                  :style="auditLogTable.columnStyle('user')"
                >
                  <div class="flex items-center gap-2">
                    <div
                      class="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center flex-shrink-0"
                    >
                      <span class="text-xs font-medium text-white">{{
                        (log.user_display || "S")[0].toUpperCase()
                      }}</span>
                    </div>
                    <div class="min-w-0">
                      <div class="text-sm font-medium text-foreground truncate">
                        {{ log.user_display || t("auditLog.system") }}
                      </div>
                      <div class="text-xs text-foreground-secondary truncate">
                        {{ log.user_email || "-" }}
                      </div>
                    </div>
                  </div>
                </td>
                <td
                  class="px-4 py-3 whitespace-nowrap text-center"
                  :style="auditLogTable.columnStyle('action')"
                >
                  <span
                    :class="getActionBadgeClass(log.action)"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  >
                    {{ t(`auditLog.actions.${log.action}`, log.action) }}
                  </span>
                </td>
                <td
                  class="px-4 py-3"
                  :style="auditLogTable.columnStyle('resource')"
                >
                  <div class="text-sm text-foreground truncate max-w-[200px]">
                    {{ log.resource_name || log.resource_id || "-" }}
                  </div>
                  <div class="text-xs text-foreground-secondary">
                    {{
                      t(
                        `auditLog.resourceTypes.${log.resource_type}`,
                        log.resource_type,
                      )
                    }}
                  </div>
                </td>
                <td
                  class="px-4 py-3 whitespace-nowrap text-center"
                  :style="auditLogTable.columnStyle('result')"
                >
                  <span
                    :class="getResultBadgeClass(log.result)"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  >
                    {{ t(`auditLog.results.${log.result}`, log.result) }}
                  </span>
                </td>
                <td
                  class="px-4 py-3 whitespace-nowrap text-center"
                  :style="auditLogTable.columnStyle('ip')"
                >
                  <span class="text-sm text-foreground-secondary font-mono">
                    {{ log.ip_address || "-" }}
                  </span>
                </td>
                <td
                  class="px-4 py-3 whitespace-nowrap text-center"
                  :style="auditLogTable.columnStyle('actions')"
                >
                  <button
                    @click="showDetail(log)"
                    class="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 text-sm font-medium"
                  >
                    {{ t("common.detail") }}
                  </button>
                </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        v-if="pagination.count > 0"
        class="flex flex-shrink-0 flex-wrap items-center justify-between gap-4 border-t border-border bg-card p-4"
      >
          <div class="flex items-center gap-2">
            <span class="text-sm text-foreground-secondary">{{
              t("common.rowsPerPage")
            }}</span>
            <select
              v-model="pageSize"
              @change="handlePageSizeChange"
              class="h-8 px-2 rounded border border-border bg-background text-sm text-foreground"
            >
              <option :value="10">10</option>
              <option :value="20">20</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
            </select>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-foreground-secondary">
              {{ t("common.showing") }} {{ startItem }}-{{ endItem }}
              {{ t("common.of") }} {{ pagination.count }}
            </span>
            <nav class="flex items-center gap-1">
              <button
                :disabled="pagination.page <= 1"
                @click="changePage(pagination.page - 1)"
                class="h-8 w-8 flex items-center justify-center rounded border border-border bg-background text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeftIcon class="w-4 h-4" />
              </button>
              <template v-for="page in visiblePages" :key="page">
                <button
                  v-if="page === '...'"
                  class="h-8 w-8 flex items-center justify-center text-slate-400"
                >
                  ...
                </button>
                <button
                  v-else
                  @click="changePage(page as number)"
                  :class="[
                    'h-8 w-8 flex items-center justify-center rounded text-sm font-medium',
                    page === pagination.page
                      ? 'bg-indigo-600 text-white'
                      : 'border border-border bg-background text-foreground-secondary hover:bg-hover',
                  ]"
                >
                  {{ page }}
                </button>
              </template>
              <button
                :disabled="pagination.page >= totalPages"
                @click="changePage(pagination.page + 1)"
                class="h-8 w-8 flex items-center justify-center rounded border border-border bg-background text-foreground-secondary hover:bg-hover disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRightIcon class="w-4 h-4" />
              </button>
            </nav>
          </div>
      </div>
    </div>

      <!-- Detail Modal -->
      <Transition name="modal">
        <div v-if="showDetailModal" class="fixed inset-0 z-50 overflow-y-auto">
          <div class="flex items-center justify-center min-h-screen px-4">
            <div
              class="fixed inset-0 bg-black/50"
              @click="showDetailModal = false"
            ></div>
            <div
              class="relative modal-surface rounded-xl shadow-xl max-w-2xl w-full"
            >
              <div
                class="flex items-center justify-between px-6 py-4 border-b border-border"
              >
                <h3 class="text-lg font-semibold text-foreground">
                  {{ t("auditLog.detail") }}
                </h3>
                <button
                  @click="showDetailModal = false"
                  class="p-1 rounded-lg text-slate-400 hover:bg-hover"
                >
                  <XMarkIcon class="h-5 w-5" />
                </button>
              </div>
              <div v-if="selectedLog" class="p-6 space-y-4">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("auditLog.timestamp") }}
                    </label>
                    <div class="text-sm text-foreground">
                      {{ formatDateTime(selectedLog.timestamp) }}
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("auditLog.user") }}
                    </label>
                    <div class="text-sm text-foreground">
                      {{ selectedLog.user_display || "System" }}
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("auditLog.action") }}
                    </label>
                    <div class="text-sm">
                      <span
                        :class="getActionBadgeClass(selectedLog.action)"
                        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      >
                        {{
                          t(
                            `auditLog.actions.${selectedLog.action}`,
                            selectedLog.action,
                          )
                        }}
                      </span>
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("auditLog.result") }}
                    </label>
                    <div class="text-sm">
                      <span
                        :class="getResultBadgeClass(selectedLog.result)"
                        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      >
                        {{
                          t(
                            `auditLog.results.${selectedLog.result}`,
                            selectedLog.result,
                          )
                        }}
                      </span>
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("auditLog.resource") }}
                    </label>
                    <div class="text-sm text-foreground">
                      {{
                        t(
                          `auditLog.resourceTypes.${selectedLog.resource_type}`,
                          selectedLog.resource_type,
                        )
                      }}:
                      {{ selectedLog.resource_name || selectedLog.resource_id }}
                    </div>
                  </div>
                  <div>
                    <label
                      class="block text-xs font-medium text-foreground-secondary mb-1"
                    >
                      {{ t("auditLog.ipAddress") }}
                    </label>
                    <div class="text-sm text-foreground font-mono">
                      {{ selectedLog.ip_address || "-" }}
                    </div>
                  </div>
                </div>

                <div>
                  <label
                    class="block text-xs font-medium text-foreground-secondary mb-1"
                  >
                    {{ t("auditLog.requestPath") }}
                  </label>
                  <div
                    class="text-sm text-foreground font-mono bg-background-secondary px-3 py-2 rounded"
                  >
                    <span
                      :class="getMethodColor(selectedLog.request_method)"
                      class="font-semibold"
                      >{{ selectedLog.request_method }}</span
                    >
                    {{ selectedLog.request_path }}
                  </div>
                </div>

                <!-- Request Details (Collapsible) -->
                <div class="border border-border rounded-lg overflow-hidden">
                  <button
                    type="button"
                    @click="showRequestDetails = !showRequestDetails"
                    class="w-full flex items-center justify-between px-4 py-3 bg-background-secondary hover:bg-hover transition-colors"
                  >
                    <span class="text-sm font-medium text-foreground">
                      {{ t("auditLog.requestDetails") }}
                    </span>
                    <ChevronDownIcon
                      :class="[
                        'w-4 h-4 text-slate-500 transition-transform',
                        showRequestDetails ? 'rotate-180' : '',
                      ]"
                    />
                  </button>
                  <Transition
                    enter-active-class="transition duration-200 ease-out"
                    enter-from-class="opacity-0 -translate-y-1"
                    enter-to-class="opacity-100 translate-y-0"
                    leave-active-class="transition duration-150 ease-in"
                    leave-from-class="opacity-100 translate-y-0"
                    leave-to-class="opacity-0 -translate-y-1"
                  >
                    <div
                      v-show="showRequestDetails"
                      class="px-4 py-3 space-y-3 bg-card"
                    >
                      <!-- Query Parameters -->
                      <div
                        v-if="
                          selectedLog.request_query &&
                          Object.keys(selectedLog.request_query).length > 0
                        "
                      >
                        <label
                          class="block text-xs font-medium text-foreground-secondary mb-1"
                        >
                          {{ t("auditLog.queryParams") }}
                        </label>
                        <pre
                          class="bg-background-secondary rounded-lg p-3 text-xs overflow-auto max-h-40 font-mono text-foreground"
                          >{{ formatJson(selectedLog.request_query) }}</pre
                        >
                      </div>
                      <!-- Request Body -->
                      <div
                        v-if="
                          selectedLog.request_body &&
                          Object.keys(selectedLog.request_body).length > 0
                        "
                      >
                        <label
                          class="block text-xs font-medium text-foreground-secondary mb-1"
                        >
                          {{ t("auditLog.requestBody") }}
                        </label>
                        <pre
                          class="bg-background-secondary rounded-lg p-3 text-xs overflow-auto max-h-60 font-mono text-foreground"
                          >{{ formatJson(selectedLog.request_body) }}</pre
                        >
                      </div>
                      <!-- User Agent -->
                      <div v-if="selectedLog.user_agent">
                        <label
                          class="block text-xs font-medium text-foreground-secondary mb-1"
                        >
                          {{ t("auditLog.userAgent") }}
                        </label>
                        <div
                          class="text-xs text-foreground-secondary bg-background-secondary px-3 py-2 rounded font-mono break-all"
                        >
                          {{ selectedLog.user_agent }}
                        </div>
                      </div>
                      <!-- Empty State -->
                      <div
                        v-if="
                          (!selectedLog.request_query ||
                            Object.keys(selectedLog.request_query).length ===
                              0) &&
                          (!selectedLog.request_body ||
                            Object.keys(selectedLog.request_body).length === 0)
                        "
                        class="text-sm text-foreground-secondary italic"
                      >
                        {{ t("auditLog.noRequestData") }}
                      </div>
                    </div>
                  </Transition>
                </div>

                <div v-if="selectedLog.details">
                  <label
                    class="block text-xs font-medium text-foreground-secondary mb-1"
                  >
                    {{ t("auditLog.description") }}
                  </label>
                  <div class="text-sm text-foreground">
                    {{ selectedLog.details }}
                  </div>
                </div>

                <div v-if="selectedLog.error_message">
                  <label class="block text-xs font-medium text-red-500 mb-1">
                    {{ t("auditLog.errorMessage") }}
                  </label>
                  <div
                    class="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded"
                  >
                    {{ selectedLog.error_message }}
                  </div>
                </div>

                <div
                  v-if="
                    selectedLog.changes &&
                    Object.keys(selectedLog.changes).length > 0
                  "
                >
                  <label
                    class="block text-xs font-medium text-foreground-secondary mb-1"
                  >
                    {{ t("auditLog.changes") }}
                  </label>
                  <pre
                    class="bg-background-secondary rounded-lg p-3 text-xs overflow-auto max-h-60 font-mono"
                    >{{ JSON.stringify(selectedLog.changes, null, 2) }}</pre
                  >
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  ArrowDownTrayIcon,
  XMarkIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CubeIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  ChartBarIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import { auditLogApi } from "@/api";
import { useAppStore } from "@/stores/app";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import ResizableSortableTh from "@/components/ResizableSortableTh.vue";

const { t } = useI18n();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

interface AuditLogItem {
  id: string;
  timestamp: string;
  user: string | null;
  user_display: string;
  user_email: string;
  user_name: string;
  action: string;
  action_display: string;
  resource_type: string;
  resource_type_display: string;
  resource_id: string;
  resource_name: string;
  result: string;
  result_display: string;
  ip_address: string;
  details: string;
  error_message: string;
  request_method: string;
  request_path: string;
  request_query: Record<string, string[]>;
  request_body: Record<string, unknown>;
  user_agent: string;
  changes: Record<string, unknown>;
}

interface Statistics {
  total_count: number;
  today_count: number;
  action_stats: Record<string, number>;
  resource_stats: Record<string, number>;
  result_stats: Record<string, number>;
}

// State
const logs = ref<AuditLogItem[]>([]);
const loading = ref(false);
const statistics = ref<Statistics | null>(null);
const showDetailModal = ref(false);
const selectedLog = ref<AuditLogItem | null>(null);
const showRequestDetails = ref(false);

// Search & Filters
const searchQuery = ref("");
const searchType = ref("all");
const showSearchTypeMenu = ref(false);
const showActionMenu = ref(false);
const showResourceMenu = ref(false);
const datePreset = ref("7d");

const filters = ref({
  start_date: "",
  end_date: "",
  action: "",
  resource_type: "",
  search: "",
  search_field: "all",
});

// Pagination
const pagination = ref({ page: 1, count: 0 });
const pageSize = ref(getPageSize("audit-log"));
const PAGE_STORAGE_KEY = "audit-log";

watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

// Search types
const searchTypes = computed(() => [
  { value: "all", label: t("common.all") },
  { value: "user", label: t("auditLog.user") },
  { value: "resource", label: t("auditLog.resource") },
  { value: "ip", label: t("auditLog.ipAddress") },
]);

const searchTypeLabel = computed(() => {
  const type = searchTypes.value.find((t) => t.value === searchType.value);
  return type?.label || t("common.all");
});

const searchPlaceholder = computed(() => {
  const placeholders: Record<string, string> = {
    all: t("auditLog.searchPlaceholder"),
    user: t("auditLog.searchUser"),
    resource: t("auditLog.searchResource"),
    ip: t("auditLog.searchIp"),
  };
  return placeholders[searchType.value] || placeholders.all;
});

// Date presets
const datePresets = computed(() => [
  { value: "today", label: t("auditLog.today") },
  { value: "7d", label: t("auditLog.last7Days") },
  { value: "30d", label: t("auditLog.last30Days") },
  { value: "custom", label: t("auditLog.custom") },
]);

// Action options
const actionOptions = [
  "create",
  "update",
  "delete",
  "login",
  "logout",
  "enable",
  "disable",
];

// Resource type options
const resourceTypeOptions = ["user", "tenant", "proxy", "license", "session"];

type AuditLogColumnKey =
  | "timestamp"
  | "user"
  | "action"
  | "resource"
  | "result"
  | "ip"
  | "actions";

// Table columns
const columns = computed(() => [
  {
    key: "timestamp" as const,
    label: t("auditLog.timestamp"),
    min: 170,
    max: 320,
    align: "center" as const,
  },
  {
    key: "user" as const,
    label: t("auditLog.user"),
    min: 210,
    max: 420,
  },
  {
    key: "action" as const,
    label: t("auditLog.action"),
    min: 130,
    max: 240,
    align: "center" as const,
  },
  {
    key: "resource" as const,
    label: t("auditLog.resource"),
    min: 240,
    max: 520,
  },
  {
    key: "result" as const,
    label: t("auditLog.result"),
    min: 120,
    max: 220,
    align: "center" as const,
  },
  {
    key: "ip" as const,
    label: t("auditLog.ipAddress"),
    min: 150,
    max: 280,
    align: "center" as const,
  },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 100,
    max: 180,
    sortable: false,
    align: "center" as const,
  },
]);

const auditLogTable = useResizableSortableTable<
  AuditLogItem,
  AuditLogColumnKey
>({
  storageKey: "hyperfilelens:audit-log:columnWidths",
  columns,
  rows: logs,
  defaultSort: { key: "timestamp", direction: "desc" },
  minTableWidth: 1120,
  getSortValue: (log, key) => {
    if (key === "timestamp") return new Date(log.timestamp).getTime();
    if (key === "user") return log.user_display || log.user_email || "";
    if (key === "resource") {
      return log.resource_name || log.resource_id || log.resource_type || "";
    }
    if (key === "ip") return log.ip_address || "";
    if (key === "actions") return "";
    return (log as any)[key] ?? "";
  },
  getColumnText: (log, key) => {
    if (key === "timestamp") return formatDateTime(log.timestamp);
    if (key === "user") return log.user_display || log.user_email || "-";
    if (key === "resource") return log.resource_name || log.resource_id || "-";
    if (key === "ip") return log.ip_address || "-";
    if (key === "actions") return t("common.detail");
    return String((log as any)[key] ?? "");
  },
});

// Computed
const totalPages = computed(() =>
  Math.ceil(pagination.value.count / pageSize.value),
);

const startItem = computed(
  () => (pagination.value.page - 1) * pageSize.value + 1,
);

const endItem = computed(() =>
  Math.min(pagination.value.page * pageSize.value, pagination.value.count),
);

const successRate = computed(() => {
  if (!statistics.value) return 0;
  const total = statistics.value.total_count;
  if (total === 0) return 0;
  const success = statistics.value.result_stats?.success || 0;
  return Math.round((success / total) * 100);
});

const statCards = computed(() => [
  {
    label: t("auditLog.totalLogs"),
    value: statistics.value?.total_count || 0,
    className: "text-foreground",
    icon: ClipboardDocumentListIcon,
  },
  {
    label: t("auditLog.todayLogs"),
    value: statistics.value?.today_count || 0,
    className: "text-blue-600",
    icon: ChartBarIcon,
  },
  {
    label: t("auditLog.successRate"),
    value: `${successRate.value}%`,
    className: "text-green-600 dark:text-green-400",
    icon: DocumentTextIcon,
  },
  {
    label: t("auditLog.failureCount"),
    value: statistics.value?.result_stats?.failure || 0,
    className: "text-red-600 dark:text-red-400",
    icon: XCircleIcon,
  },
]);

const hasActiveFilters = computed(() => {
  return (
    filters.value.action ||
    filters.value.resource_type ||
    searchQuery.value ||
    datePreset.value !== "7d"
  );
});

const visiblePages = computed(() => {
  const pages: (number | string)[] = [];
  const current = pagination.value.page;
  const total = totalPages.value;

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    if (current > 3) pages.push("...");

    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);

    for (let i = start; i <= end; i++) pages.push(i);

    if (current < total - 2) pages.push("...");
    pages.push(total);
  }

  return pages;
});

// Methods
const fetchLogs = async () => {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      page: pagination.value.page,
      page_size: pageSize.value,
    };
    if (filters.value.start_date) params.start_date = filters.value.start_date;
    if (filters.value.end_date) params.end_date = filters.value.end_date;
    if (filters.value.action) params.action = filters.value.action;
    if (filters.value.resource_type)
      params.resource_type = filters.value.resource_type;
    if (filters.value.search) {
      params.search = filters.value.search;
      params.search_field = filters.value.search_field;
    }

    const response = await auditLogApi.list(params);
    logs.value = response.data.results || response.data;
    pagination.value.count = response.data.count || logs.value.length;
  } catch (error) {
    console.error("Failed to fetch audit logs:", error);
    appStore.showToast({ type: "error", title: t("common.fetchFailed") });
  } finally {
    loading.value = false;
  }
};

const fetchStatistics = async () => {
  try {
    const response = await auditLogApi.statistics();
    statistics.value = response.data;
  } catch (error) {
    console.error("Failed to fetch statistics:", error);
  }
};

const refreshAuditLogs = () => {
  fetchLogs();
  fetchStatistics();
};

const handleSearch = () => {
  filters.value.search = searchQuery.value;
  filters.value.search_field = searchType.value;
  pagination.value.page = 1;
  fetchLogs();
};

const selectSearchType = (type: string) => {
  searchType.value = type;
  showSearchTypeMenu.value = false;
};

const selectDatePreset = (preset: string) => {
  datePreset.value = preset;

  const today = new Date();
  const formatDate = (d: Date) => d.toISOString().split("T")[0];

  if (preset === "today") {
    filters.value.start_date = formatDate(today);
    filters.value.end_date = formatDate(today);
    pagination.value.page = 1;
    fetchLogs();
  } else if (preset === "7d") {
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);
    filters.value.start_date = formatDate(weekAgo);
    filters.value.end_date = formatDate(today);
    pagination.value.page = 1;
    fetchLogs();
  } else if (preset === "30d") {
    const monthAgo = new Date(today);
    monthAgo.setDate(monthAgo.getDate() - 30);
    filters.value.start_date = formatDate(monthAgo);
    filters.value.end_date = formatDate(today);
    pagination.value.page = 1;
    fetchLogs();
  }
};

const applyCustomDate = () => {
  pagination.value.page = 1;
  fetchLogs();
};

const selectAction = (action: string) => {
  filters.value.action = action;
  showActionMenu.value = false;
  pagination.value.page = 1;
  fetchLogs();
};

const selectResourceType = (type: string) => {
  filters.value.resource_type = type;
  showResourceMenu.value = false;
  pagination.value.page = 1;
  fetchLogs();
};

const resetFilters = () => {
  searchQuery.value = "";
  searchType.value = "all";
  datePreset.value = "7d";
  filters.value = {
    start_date: "",
    end_date: "",
    action: "",
    resource_type: "",
    search: "",
    search_field: "all",
  };
  pagination.value.page = 1;
  selectDatePreset("7d");
};

const changePage = (page: number) => {
  pagination.value.page = page;
  fetchLogs();
};

const handlePageSizeChange = () => {
  pagination.value.page = 1;
  fetchLogs();
};

const showDetail = async (log: AuditLogItem) => {
  // 先显示基本信息（列表中的数据）
  selectedLog.value = log;
  showRequestDetails.value = false;
  showDetailModal.value = true;

  // 然后异步获取详情（包含 request_query 和 request_body）
  try {
    const response = await auditLogApi.retrieve(log.id);
    selectedLog.value = response.data;
  } catch (error) {
    console.error("Failed to fetch audit log detail:", error);
    // 失败时仍然显示列表中的基本信息
  }
};

const exportLogs = async (format: "json" | "csv") => {
  try {
    const response = await auditLogApi.export(format);
    const blob = new Blob([response.data], {
      type: format === "csv" ? "text/csv" : "application/json",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `audit_logs.${format}`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Failed to export logs:", error);
    appStore.showToast({ type: "error", title: t("common.exportFailed") });
  }
};

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleString();
};

const formatJson = (data: unknown) => {
  if (!data) return "{}";
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return String(data);
  }
};

const getActionBadgeClass = (action: string) => {
  const classes: Record<string, string> = {
    create:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    update: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    delete: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    login:
      "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
    logout: "bg-slate-100 text-slate-700",
    enable:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    disable:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  };
  return classes[action] || "bg-slate-100 text-slate-700";
};

const getResultBadgeClass = (result: string) => {
  const classes: Record<string, string> = {
    success:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failure: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    partial:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  };
  return classes[result] || "bg-slate-100 text-slate-700";
};

const getMethodColor = (method: string) => {
  const colors: Record<string, string> = {
    GET: "text-green-600 dark:text-green-400",
    POST: "text-blue-600 dark:text-blue-400",
    PUT: "text-yellow-600 dark:text-yellow-400",
    PATCH: "text-orange-600 dark:text-orange-400",
    DELETE: "text-red-600 dark:text-red-400",
  };
  return colors[method] || "text-foreground-secondary";
};

// Close dropdowns on outside click
const handleClickOutside = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (!target.closest(".relative")) {
    showSearchTypeMenu.value = false;
    showActionMenu.value = false;
    showResourceMenu.value = false;
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
  selectDatePreset("7d");
  fetchStatistics();
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<style scoped>
/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.15s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.2s ease;
}
.modal-enter-from .relative,
.modal-leave-to .relative {
  transform: scale(0.95);
}

/* Prevent text selection during resize */
.resizing {
  user-select: none;
}
</style>
