<script setup lang="ts">
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  PencilSquareIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import BackupTaskEditBasicSection from "./edit/BackupTaskEditBasicSection.vue";
import BackupTaskEditExecutionSection from "./edit/BackupTaskEditExecutionSection.vue";
import BackupTaskEditFilesSection from "./edit/BackupTaskEditFilesSection.vue";
import BackupTaskEditReadonlySection from "./edit/BackupTaskEditReadonlySection.vue";
import BackupTaskEditScheduleRetentionSection from "./edit/BackupTaskEditScheduleRetentionSection.vue";
import BackupTaskEditSecuritySection from "./edit/BackupTaskEditSecuritySection.vue";
import type { BackupTask } from "@/types/backup";
import type { ProxyNode } from "@/types/proxy";
import type { Repository } from "@/types/repository";
import type { SourceResource } from "@/types/sourceResource";

defineProps<{
  task: BackupTask;
  loading: boolean;
  saving: boolean;
  source: SourceResource | null;
  repository: Repository | null;
  sourceRows: Array<[string, any]>;
  repositoryRows: Array<[string, any]>;
  policies: Array<Record<string, any>>;
  proxies: ProxyNode[];
  selectedPolicy: Record<string, any> | null;
  policyScheduleSummary: string;
  policyRetentionSummary: string;
  retentionFields: ReadonlyArray<{ key: string; label: string }>;
  canUseAutoPlacement: boolean;
}>();

const form = defineModel<any>("form", { required: true });

defineEmits<{
  close: [];
  submit: [];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="$emit('close')" />
      <form
        class="relative modal-surface w-full max-w-5xl max-h-[90vh] rounded-xl shadow-xl border border-border overflow-hidden flex flex-col"
        @submit.prevent="$emit('submit')"
      >
        <div
          class="px-6 py-4 border-b border-border flex items-start justify-between gap-4"
        >
          <div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ t("backupTasks.edit.title") }}
            </h2>
            <p class="mt-1 text-sm text-foreground-secondary">
              {{ t("backupTasks.edit.subtitle") }}
            </p>
          </div>
          <button
            type="button"
            @click="$emit('close')"
            class="p-2 hover:bg-background-tertiary rounded-lg"
          >
            <XCircleIcon class="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div v-if="loading" class="p-10 text-center text-foreground-secondary">
          {{ t("common.loading") }}
        </div>

        <div v-else class="p-6 overflow-y-auto space-y-5">
          <BackupTaskEditReadonlySection
            :task="task"
            :source="source"
            :repository="repository"
            :source-rows="sourceRows"
            :repository-rows="repositoryRows"
          />

          <BackupTaskEditBasicSection v-model:form="form" />

          <BackupTaskEditExecutionSection
            v-model:form="form"
            :proxies="proxies"
            :can-use-auto-placement="canUseAutoPlacement"
          />

          <BackupTaskEditScheduleRetentionSection
            v-model:form="form"
            :policies="policies"
            :selected-policy="selectedPolicy"
            :policy-schedule-summary="policyScheduleSummary"
            :policy-retention-summary="policyRetentionSummary"
            :retention-fields="retentionFields"
          />

          <BackupTaskEditFilesSection v-model:form="form" />

          <BackupTaskEditSecuritySection v-model:form="form" />
        </div>

        <div
          class="px-6 py-4 border-t border-border flex items-center justify-end gap-3"
        >
          <button
            type="button"
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-foreground-secondary border border-border rounded-lg hover:bg-hover"
          >
            {{ t("common.cancel") }}
          </button>
          <button
            type="submit"
            :disabled="saving || loading"
            class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowPathIcon v-if="saving" class="w-4 h-4 animate-spin" />
            <PencilSquareIcon v-else class="w-4 h-4" />
            {{ saving ? t("common.saving") : t("common.save") }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>
