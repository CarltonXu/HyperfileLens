<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  ArrowDownTrayIcon,
  ArchiveBoxIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  EyeSlashIcon,
  FolderIcon,
  LockClosedIcon,
  ShieldCheckIcon,
} from "@heroicons/vue/24/outline";
import { recoveryExportsApi } from "@/api";

const route = useRoute();
const { t } = useI18n();

const exportId = computed(() => String(route.params.id || ""));
const token = computed(() => String(route.query.token || ""));
const loading = ref(true);
const downloading = ref(false);
const password = ref("");
const showPassword = ref(false);
const errorMessage = ref("");
const exportInfo = ref<any>(null);

function formatBytes(value?: number | string | null) {
  const bytes = Number(value || 0);
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / 1024 ** index;
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function filenameFromDisposition(disposition?: string) {
  if (!disposition) return "";
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] || "";
}

async function blobErrorMessage(data: unknown) {
  if (!(data instanceof Blob)) return "";
  try {
    const text = await data.text();
    const parsed = JSON.parse(text);
    return parsed.message || parsed.error || text;
  } catch {
    return "";
  }
}

async function fetchInfo() {
  loading.value = true;
  errorMessage.value = "";
  try {
    if (!exportId.value || !token.value) {
      errorMessage.value = t("sharedRecoveryExport.invalidLink");
      return;
    }
    const response = await recoveryExportsApi.publicInfo(exportId.value, token.value);
    exportInfo.value = response.data;
  } catch (error: any) {
    errorMessage.value =
      error?.response?.data?.message ||
      error?.response?.data?.error ||
      t("sharedRecoveryExport.loadFailed");
  } finally {
    loading.value = false;
  }
}

async function downloadExport() {
  if (!exportInfo.value || downloading.value) return;
  if (!password.value.trim()) {
    errorMessage.value = t("sharedRecoveryExport.passwordRequired");
    return;
  }

  downloading.value = true;
  errorMessage.value = "";
  try {
    const response = await recoveryExportsApi.publicDownload(exportId.value, {
      token: token.value,
      password: password.value,
    });
    const blob = new Blob([response.data], {
      type: String(response.headers["content-type"] || "application/octet-stream"),
    });
    const filename =
      filenameFromDisposition(String(response.headers["content-disposition"] || "")) ||
      exportInfo.value.file_name ||
      `recovery-export-${exportId.value}.zip`;
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error: any) {
    errorMessage.value =
      (await blobErrorMessage(error?.response?.data)) ||
      error?.response?.data?.message ||
      error?.response?.data?.error ||
      t("sharedRecoveryExport.downloadFailed");
  } finally {
    downloading.value = false;
  }
}

onMounted(fetchInfo);
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <header class="border-b border-border bg-card">
      <div class="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-white">
            H
          </div>
          <div>
            <p class="text-sm font-semibold text-foreground">HyperFileLens</p>
            <p class="text-xs text-foreground-secondary">{{ t("sharedRecoveryExport.productSubtitle") }}</p>
          </div>
        </div>
        <span class="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-foreground-secondary">
          <ShieldCheckIcon class="h-4 w-4 text-emerald-500" />
          {{ t("sharedRecoveryExport.protected") }}
        </span>
      </div>
    </header>

    <main class="mx-auto grid max-w-5xl gap-5 px-5 py-8 lg:grid-cols-[1fr_360px]">
      <section class="rounded-lg border border-border bg-card p-5 shadow-sm">
        <div v-if="loading" class="py-16 text-center text-sm text-foreground-secondary">
          {{ t("common.loading") }}
        </div>

        <div v-else-if="errorMessage && !exportInfo" class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
          <div class="flex items-start gap-3">
            <ExclamationTriangleIcon class="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p class="font-medium">{{ t("sharedRecoveryExport.unavailable") }}</p>
              <p class="mt-1 text-sm">{{ errorMessage }}</p>
            </div>
          </div>
        </div>

        <template v-else-if="exportInfo">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="text-xs font-medium uppercase tracking-wide text-primary">{{ t("sharedRecoveryExport.sharedPackage") }}</p>
              <h1 class="mt-2 break-words text-2xl font-semibold text-foreground">
                {{ exportInfo.name || exportInfo.file_name || t("sharedRecoveryExport.untitled") }}
              </h1>
              <p class="mt-2 text-sm text-foreground-secondary">
                {{ exportInfo.description || t("sharedRecoveryExport.defaultDescription") }}
              </p>
            </div>
            <span
              :class="[
                'rounded-full px-2.5 py-1 text-xs font-medium',
                exportInfo.is_downloadable
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                  : 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
              ]"
            >
              {{ exportInfo.is_downloadable ? t("sharedRecoveryExport.ready") : t("sharedRecoveryExport.notReady") }}
            </span>
          </div>

          <div class="mt-5 grid gap-3 sm:grid-cols-3">
            <div class="rounded-lg border border-border bg-background px-3 py-3">
              <div class="flex items-center gap-2 text-xs text-foreground-muted">
                <ArchiveBoxIcon class="h-4 w-4" />
                {{ t("sharedRecoveryExport.packageSize") }}
              </div>
              <p class="mt-2 text-sm font-semibold text-foreground">{{ formatBytes(exportInfo.package_size) }}</p>
            </div>
            <div class="rounded-lg border border-border bg-background px-3 py-3">
              <div class="flex items-center gap-2 text-xs text-foreground-muted">
                <FolderIcon class="h-4 w-4" />
                {{ t("sharedRecoveryExport.selectedPaths") }}
              </div>
              <p class="mt-2 text-sm font-semibold text-foreground">{{ exportInfo.selected_path_count || 0 }}</p>
            </div>
            <div class="rounded-lg border border-border bg-background px-3 py-3">
              <div class="flex items-center gap-2 text-xs text-foreground-muted">
                <ClockIcon class="h-4 w-4" />
                {{ t("sharedRecoveryExport.expiresAt") }}
              </div>
              <p class="mt-2 text-sm font-semibold text-foreground">{{ formatDate(exportInfo.share_expires_at || exportInfo.expires_at) }}</p>
            </div>
          </div>

          <div class="mt-5 grid gap-4 lg:grid-cols-2">
            <section class="rounded-lg border border-border bg-background p-4">
              <h2 class="text-sm font-semibold text-foreground">{{ t("sharedRecoveryExport.snapshot") }}</h2>
              <dl class="mt-3 space-y-3 text-sm">
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("sharedRecoveryExport.snapshotName") }}</dt>
                  <dd class="mt-1 break-all text-foreground-secondary">{{ exportInfo.snapshot_name || "-" }}</dd>
                </div>
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("sharedRecoveryExport.sourcePath") }}</dt>
                  <dd class="mt-1 break-all text-foreground-secondary">{{ exportInfo.snapshot_source_path || "-" }}</dd>
                </div>
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("sharedRecoveryExport.snapshotTime") }}</dt>
                  <dd class="mt-1 text-foreground-secondary">{{ formatDate(exportInfo.snapshot_created_at) }}</dd>
                </div>
              </dl>
            </section>

            <section class="rounded-lg border border-border bg-background p-4">
              <h2 class="text-sm font-semibold text-foreground">{{ t("sharedRecoveryExport.package") }}</h2>
              <dl class="mt-3 space-y-3 text-sm">
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("sharedRecoveryExport.fileName") }}</dt>
                  <dd class="mt-1 break-all text-foreground-secondary">{{ exportInfo.file_name || "-" }}</dd>
                </div>
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("sharedRecoveryExport.repository") }}</dt>
                  <dd class="mt-1 text-foreground-secondary">{{ exportInfo.repository_name || "-" }}</dd>
                </div>
                <div>
                  <dt class="text-xs text-foreground-muted">{{ t("sharedRecoveryExport.downloads") }}</dt>
                  <dd class="mt-1 text-foreground-secondary">{{ exportInfo.download_count || 0 }}</dd>
                </div>
              </dl>
            </section>
          </div>

          <section class="mt-5 rounded-lg border border-border bg-background p-4">
            <div class="mb-3 flex items-center justify-between">
              <h2 class="text-sm font-semibold text-foreground">{{ t("sharedRecoveryExport.selectedPaths") }}</h2>
              <span class="text-xs text-foreground-secondary">{{ exportInfo.selected_path_count || 0 }}</span>
            </div>
            <div class="max-h-48 overflow-auto rounded-lg border border-border bg-card">
              <p
                v-for="path in exportInfo.selected_paths || []"
                :key="path"
                class="border-b border-border px-3 py-2 font-mono text-xs text-foreground-secondary last:border-b-0"
              >
                {{ path }}
              </p>
            </div>
          </section>
        </template>
      </section>

      <aside class="h-fit rounded-lg border border-border bg-card p-5 shadow-sm">
        <div class="flex items-center gap-2">
          <LockClosedIcon class="h-5 w-5 text-primary" />
          <h2 class="text-base font-semibold text-foreground">{{ t("sharedRecoveryExport.downloadTitle") }}</h2>
        </div>
        <p class="mt-2 text-sm text-foreground-secondary">{{ t("sharedRecoveryExport.downloadDescription") }}</p>

        <label class="mt-5 block">
          <span class="text-sm font-medium text-foreground">{{ t("sharedRecoveryExport.password") }}</span>
          <div class="relative mt-1">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              class="w-full rounded-lg border border-border bg-background px-3 py-2 pr-10 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              :placeholder="t('sharedRecoveryExport.passwordPlaceholder')"
              @keydown.enter="downloadExport"
            />
            <button
              type="button"
              class="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-lg text-foreground-muted hover:text-foreground"
              :title="showPassword ? t('sharedRecoveryExport.hidePassword') : t('sharedRecoveryExport.showPassword')"
              @click="showPassword = !showPassword"
            >
              <EyeSlashIcon v-if="showPassword" class="h-4 w-4" />
              <EyeIcon v-else class="h-4 w-4" />
            </button>
          </div>
        </label>

        <p v-if="errorMessage && exportInfo" class="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
          {{ errorMessage }}
        </p>

        <button
          class="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="loading || downloading || !exportInfo?.is_downloadable"
          @click="downloadExport"
        >
          <ArrowDownTrayIcon class="h-4 w-4" />
          {{ downloading ? t("sharedRecoveryExport.downloading") : t("sharedRecoveryExport.download") }}
        </button>
      </aside>
    </main>
  </div>
</template>
