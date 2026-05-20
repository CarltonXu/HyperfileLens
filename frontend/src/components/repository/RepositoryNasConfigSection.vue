<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { ProxyNode } from "@/types/proxy";
import { ExclamationCircleIcon } from "@heroicons/vue/24/outline";

defineProps<{
  newRepo: {
    bound_node: string | null;
    nas_config: {
      server: string;
      export_path: string;
      mount_type: "nfs" | "cifs";
      mount_options: string;
      username: string;
      password: string;
    };
  };
  formErrors: Record<string, string>;
  availableSyncProxies: ProxyNode[];
  isEditMode: boolean;
}>();

defineEmits<{
  clearError: [field: string];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="space-y-4 p-4 rounded-xl border border-border">
    <div
      class="flex items-start gap-2 text-sm text-purple-700 dark:text-purple-400 bg-purple-50 rounded-lg p-3 border-l-4 border-purple-400"
    >
      <ExclamationCircleIcon class="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        <p class="font-medium">{{ t("repository.nas.hint") }}</p>
        <p class="mt-1 text-xs text-purple-600">
          {{ t("repository.nas.hintDetail") }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground mb-1">{{
        t("repository.nas.mountType")
      }}</label>
      <div class="grid grid-cols-2 gap-3">
        <button
          @click="newRepo.nas_config.mount_type = 'nfs'"
          :class="[
            'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
            newRepo.nas_config.mount_type === 'nfs'
              ? 'border-purple-500 dark:border-purple-500 bg-purple-50 text-purple-700 dark:text-purple-400'
              : 'border-border text-foreground-secondary hover:border-border-secondary dark:hover:border-slate-500',
          ]"
        >
          NFS
        </button>
        <button
          @click="newRepo.nas_config.mount_type = 'cifs'"
          :class="[
            'flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all text-sm font-medium',
            newRepo.nas_config.mount_type === 'cifs'
              ? 'border-purple-500 dark:border-purple-500 bg-purple-50 text-purple-700 dark:text-purple-400'
              : 'border-border text-foreground-secondary hover:border-border-secondary dark:hover:border-slate-500',
          ]"
        >
          CIFS/SMB
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm font-medium text-foreground mb-1"
          >{{ t("repository.nas.server") }} *</label
        >
        <input
          v-model="newRepo.nas_config.server"
          type="text"
          placeholder="192.168.1.100 或 nas.example.com"
          :class="[
            'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
            formErrors.server
              ? 'border-red-300 focus:ring-red-500'
              : 'border-border focus:ring-blue-500',
          ]"
          @input="$emit('clearError', 'server')"
        />
        <p
          v-if="formErrors.server"
          class="mt-1 text-xs text-red-500 dark:text-red-400"
        >
          {{ formErrors.server }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1"
          >{{ t("repository.nas.exportPath") }} *</label
        >
        <input
          v-model="newRepo.nas_config.export_path"
          type="text"
          :placeholder="
            newRepo.nas_config.mount_type === 'nfs'
              ? '/export/backup'
              : '/share/backup'
          "
          :class="[
            'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
            formErrors.export_path
              ? 'border-red-300 focus:ring-red-500'
              : 'border-border focus:ring-blue-500',
          ]"
          @input="$emit('clearError', 'export_path')"
        />
        <p
          v-if="formErrors.export_path"
          class="mt-1 text-xs text-red-500 dark:text-red-400"
        >
          {{ formErrors.export_path }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground mb-1">{{
        t("repository.nas.mountOptions")
      }}</label>
      <input
        v-model="newRepo.nas_config.mount_options"
        type="text"
        :placeholder="
          newRepo.nas_config.mount_type === 'nfs'
            ? 'rw,hard,intr'
            : 'vers=3.0,iocharset=utf8'
        "
        class="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("repository.nas.mountOptionsHint") }}
      </p>
    </div>

    <div
      v-if="newRepo.nas_config.mount_type === 'cifs'"
      class="grid grid-cols-2 gap-4 p-3 bg-background/50 rounded-lg"
    >
      <div>
        <label class="block text-sm font-medium text-foreground mb-1"
          >{{ t("repository.nas.username") }} *</label
        >
        <input
          v-model="newRepo.nas_config.username"
          type="text"
          placeholder="username"
          :class="[
            'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
            formErrors.username
              ? 'border-red-300 focus:ring-red-500'
              : 'border-border focus:ring-blue-500',
          ]"
          @input="$emit('clearError', 'username')"
        />
        <p
          v-if="formErrors.username"
          class="mt-1 text-xs text-red-500 dark:text-red-400"
        >
          {{ formErrors.username }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-foreground mb-1">
          {{ t("repository.nas.password") }}
          <span v-if="!isEditMode">*</span>
        </label>
        <input
          v-model="newRepo.nas_config.password"
          type="password"
          placeholder="••••••••"
          :class="[
            'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
            formErrors.password
              ? 'border-red-300 focus:ring-red-500'
              : 'border-border focus:ring-blue-500',
          ]"
          @input="$emit('clearError', 'password')"
        />
        <p
          v-if="isEditMode && !formErrors.password"
          class="mt-1 text-xs text-foreground-secondary"
        >
          {{ t("repository.s3.secretKeyEditHint") }}
        </p>
        <p
          v-if="formErrors.password"
          class="mt-1 text-xs text-red-500 dark:text-red-400"
        >
          {{ formErrors.password }}
        </p>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-foreground mb-1"
        >{{ t("repository.boundSyncProxy") }} *</label
      >
      <select
        v-model="newRepo.bound_node"
        :class="[
          'w-full px-3 py-2 text-sm border rounded-lg bg-background/50 text-foreground focus:outline-none focus:ring-2',
          formErrors.bound_node
            ? 'border-red-300 focus:ring-red-500'
            : 'border-border focus:ring-blue-500',
        ]"
        @change="$emit('clearError', 'bound_node')"
      >
        <option class="bg-background/50" value="">
          {{ t("repository.selectSyncProxy") }}
        </option>
        <option
          class="bg-background/50"
          v-for="proxy in availableSyncProxies"
          :key="proxy.id"
          :value="proxy.id"
        >
          {{ proxy.name }} ({{ proxy.hostname || proxy.id }}) -
          {{
            proxy.is_online
              ? t("proxies.status.online")
              : t("proxies.status.offline")
          }}
        </option>
      </select>
      <p
        v-if="formErrors.bound_node"
        class="mt-1 text-xs text-red-500 dark:text-red-400"
      >
        {{ formErrors.bound_node }}
      </p>
      <p class="text-xs text-foreground-secondary mt-1">
        {{ t("repository.boundSyncProxyHint") }}
      </p>
      <p
        v-if="availableSyncProxies.length === 0"
        class="text-xs text-amber-600 mt-1"
      >
        {{
          t("repository.noOnlineSyncProxy") ||
          "No online Sync Proxies available. Please ensure your Sync Proxy is connected."
        }}
      </p>
    </div>
  </div>
</template>
