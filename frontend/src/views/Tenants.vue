<template>
  <div class="space-y-6">
    <TenantToolbar
      v-model:search-query="searchQuery"
      v-model:status-filter="statusFilter"
      :loading="loading"
      @search="debouncedSearch"
      @filter="fetchTenants"
      @refresh="fetchTenants"
      @create="openCreateDialog"
    />

    <TenantList
      :loading="loading"
      :tenants="tenants"
      :tenant-columns="tenantColumns"
      :tenant-table="tenantTable"
      :pagination="pagination"
      :total-pages="totalPages"
      :displayed-pages="displayedPages"
      :get-status-class="getStatusClass"
      :format-date="formatDate"
      @edit="openEditDialog"
      @users="openUsersDialog"
      @stats="viewTenantStats"
      @activate="activateTenant"
      @deactivate="deactivateTenant"
      @delete="confirmDeleteTenant"
      @previous="prevPage"
      @next="nextPage"
      @page="goToPage"
      @pageSizeChange="handlePageSizeChange"
    />

    <TenantFormDialog
      :show="showDialog"
      :editing-tenant="editingTenant"
      :form-data="formData"
      :saving="saving"
      @close="closeDialog"
      @save="saveTenant"
    />

    <TenantStatsDialog
      :show="showStatsDrawer"
      :tenant="statsTenant"
      :stats-data="statsData"
      :loading="loadingStats"
      :format-bytes="formatBytes"
      @close="closeStatsDrawer"
    />

    <TenantUsersDrawer
      v-model:show-add-user-form="showAddUserForm"
      v-model:new-user-email="newUserEmail"
      v-model:new-user-role="newUserRole"
      :show="showUsersDrawer"
      :tenant="usersTenant"
      :users="tenantUsers"
      :loading="loadingUsers"
      :user-candidates="userCandidates"
      :loading-user-candidates="loadingUserCandidates"
      :selected-user-candidates="selectedUserCandidates"
      :current-user-id="currentUserId"
      :get-initials="getInitials"
      :get-display-name="getDisplayName"
      @close="closeUsersDrawer"
      @add-user="handleAddUser"
      @search-user-candidates="searchUserCandidates"
      @select-user-candidate="selectUserCandidate"
      @remove-selected-user-candidate="removeSelectedUserCandidate"
      @update-role="updateUserRole"
      @remove-user="confirmRemoveUser"
    />

    <!-- Remove User Confirmation -->
    <TransitionRoot appear :show="showRemoveUserConfirm" as="template">
      <Dialog
        as="div"
        class="relative z-[60]"
        @close="showRemoveUserConfirm = false"
      >
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div
            class="fixed inset-0 bg-slate-900/75 dark:bg-slate-900/75 transition-opacity"
          />
        </TransitionChild>

        <div class="fixed inset-0 z-[60] overflow-y-auto">
          <div class="flex min-h-full items-center justify-center p-4">
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enter-to="opacity-100 translate-y-0 sm:scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 translate-y-0 sm:scale-100"
              leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel
                class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-sm sm:p-6"
              >
                <div>
                  <div
                    class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100"
                  >
                    <ExclamationTriangleIcon
                      class="h-6 w-6 text-red-600"
                      aria-hidden="true"
                    />
                  </div>
                  <div class="mt-3 text-center sm:mt-5">
                    <DialogTitle
                      as="h3"
                      class="text-base font-semibold leading-6 text-foreground"
                    >
                      {{ t("tenants.confirmRemoveUser") }}
                    </DialogTitle>
                    <div class="mt-2">
                      <p class="text-sm text-foreground-secondary">
                        {{
                          t("tenants.confirmRemoveUserDesc", {
                            email: removingUser?.email,
                          })
                        }}
                      </p>
                    </div>
                  </div>
                </div>
                <div
                  class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3"
                >
                  <button
                    type="button"
                    class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:mt-0 transition-colors"
                    @click="showRemoveUserConfirm = false"
                  >
                    {{ t("common.cancel") }}
                  </button>
                  <button
                    type="button"
                    class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500"
                    @click="executeRemoveUser"
                  >
                    {{ t("common.remove") }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>

    <!-- Delete Confirmation -->
    <TransitionRoot appear :show="showDeleteConfirm" as="template">
      <Dialog as="div" class="relative z-10" @close="closeDeleteConfirm">
        <TransitionChild
          as="template"
          enter="duration-300 ease-out"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="duration-200 ease-in"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div
            class="fixed inset-0 bg-slate-900/75 dark:bg-slate-900/75 transition-opacity"
          />
        </TransitionChild>

        <div class="fixed inset-0 z-10 overflow-y-auto">
          <div
            class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
          >
            <TransitionChild
              as="template"
              enter="duration-300 ease-out"
              enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enter-to="opacity-100 translate-y-0 sm:scale-100"
              leave="duration-200 ease-in"
              leave-from="opacity-100 translate-y-0 sm:scale-100"
              leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel
                class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
              >
                <div class="sm:flex sm:items-start">
                  <div
                    class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10"
                  >
                    <ExclamationTriangleIcon
                      class="h-6 w-6 text-red-600"
                      aria-hidden="true"
                    />
                  </div>
                  <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                    <DialogTitle
                      as="h3"
                      class="text-base font-semibold leading-6 text-foreground"
                    >
                      {{ t("common.confirmDelete") }}
                    </DialogTitle>
                    <div class="mt-2">
                      <p class="text-sm text-foreground-secondary">
                        {{
                          t("tenants.confirmDelete", {
                            name: deletingTenant?.name,
                          })
                        }}
                      </p>
                    </div>
                  </div>
                </div>
                <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                  <button
                    type="button"
                    :disabled="deleting"
                    class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:ml-3 sm:w-auto disabled:opacity-50"
                    @click="deleteTenant"
                  >
                    {{ deleting ? t("common.deleting") : t("common.delete") }}
                  </button>
                  <button
                    type="button"
                    class="mt-3 inline-flex w-full justify-center rounded-md bg-card px-3 py-2 text-sm font-semibold text-foreground shadow-sm ring-1 ring-inset ring-border hover:bg-hover sm:mt-0 sm:w-auto"
                    :disabled="deleting"
                    @click="() => closeDeleteConfirm()"
                  >
                    {{ t("common.cancel") }}
                  </button>
                </div>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionRoot,
} from "@headlessui/vue";
import { ExclamationTriangleIcon } from "@heroicons/vue/24/outline";
import { tenantsApi } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { useAppStore } from "@/stores/app";
import type { Tenant } from "@/types/tenant";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import TenantFormDialog from "@/components/tenants/TenantFormDialog.vue";
import TenantList from "@/components/tenants/TenantList.vue";
import TenantStatsDialog from "@/components/tenants/TenantStatsDialog.vue";
import TenantToolbar from "@/components/tenants/TenantToolbar.vue";
import TenantUsersDrawer from "@/components/tenants/TenantUsersDrawer.vue";
import { getApiErrorMessage } from "@/utils/errors";

const { t } = useI18n();
const authStore = useAuthStore();
const appStore = useAppStore();
const { getPageSize, setPageSize } = usePagination();

const showToast = (
  message: string,
  type: "success" | "error" | "warning" | "info" = "info",
) => {
  appStore.showToast({ type, title: message });
};

// State
const tenants = ref<Tenant[]>([]);
const loading = ref(true);
const saving = ref(false);
const deleting = ref(false);
const showDialog = ref(false);
const showDeleteConfirm = ref(false);
const showStatsDrawer = ref(false);
const showUsersDrawer = ref(false);
const loadingStats = ref(false);
const loadingUsers = ref(false);
const editingTenant = ref<Tenant | null>(null);
const deletingTenant = ref<Tenant | null>(null);
const statsTenant = ref<Tenant | null>(null);
const statsData = ref<any>(null);
const usersTenant = ref<Tenant | null>(null);
const tenantUsers = ref<any[]>([]);
const userCandidates = ref<any[]>([]);
const selectedUserCandidates = ref<any[]>([]);
const searchQuery = ref("");
const statusFilter = ref("");
const searchTimeout = ref<number | null>(null);
const userCandidateSearchTimeout = ref<number | null>(null);
const loadingUserCandidates = ref(false);

const pagination = ref({
  page: 1,
  pageSize: getPageSize("tenants"),
  total: 0,
});
const PAGE_STORAGE_KEY = "tenants";

// Watch for page size changes and save to localStorage
watch(
  () => pagination.value.pageSize,
  (newSize) => {
    setPageSize(newSize, PAGE_STORAGE_KEY);
  },
);

const formData = ref({
  name: "",
  slug: "",
  description: "",
  contact_email: "",
  max_users: null as number | null,
  max_proxies: null as number | null,
  max_repositories: null as number | null,
  max_storage_gb: null as number | null,
});

// Computed
const totalPages = computed(() =>
  Math.ceil(pagination.value.total / pagination.value.pageSize),
);
const displayedPages = computed(() => {
  const pages: number[] = [];
  const start = Math.max(1, pagination.value.page - 2);
  const end = Math.min(totalPages.value, pagination.value.page + 2);
  for (let i = start; i <= end; i++) pages.push(i);
  return pages;
});

type TenantColumnKey =
  | "name"
  | "status"
  | "owner"
  | "user_count"
  | "proxy_count"
  | "created_at"
  | "actions";

const tenantColumns = computed(() => [
  { key: "name" as const, label: t("tenants.tenantName"), min: 260, max: 620 },
  { key: "status" as const, label: t("tenants.status"), min: 130, max: 240 },
  { key: "owner" as const, label: t("tenants.owner"), min: 220, max: 460 },
  {
    key: "user_count" as const,
    label: t("tenants.userCount"),
    min: 140,
    max: 260,
  },
  {
    key: "proxy_count" as const,
    label: t("tenants.proxyCount"),
    min: 140,
    max: 260,
  },
  {
    key: "created_at" as const,
    label: t("tenants.createdAt"),
    min: 190,
    max: 320,
  },
  {
    key: "actions" as const,
    label: t("common.actions"),
    min: 100,
    max: 180,
    sortable: false,
    align: "right" as const,
  },
]);

const tenantTable = useResizableSortableTable<Tenant, TenantColumnKey>({
  storageKey: "hyperfilelens:tenants:columnWidths",
  columns: tenantColumns,
  rows: tenants,
  defaultSort: { key: "name" },
  minTableWidth: 980,
  getSortValue: (tenant, key) => {
    if (key === "owner") return tenant.owner_name || tenant.owner_email || "";
    if (key === "created_at")
      return tenant.created_at ? new Date(tenant.created_at).getTime() : 0;
    if (key === "actions") return "";
    return (tenant as any)[key] ?? "";
  },
  getColumnText: (tenant, key) => {
    if (key === "owner") return tenant.owner_name || tenant.owner_email || "-";
    if (key === "user_count")
      return `${tenant.user_count || 0} / ${tenant.max_users || "∞"}`;
    if (key === "proxy_count")
      return `${tenant.proxy_count || 0} / ${tenant.max_proxies || "∞"}`;
    if (key === "created_at") return formatDate(tenant.created_at);
    if (key === "actions") return t("common.actions");
    return String((tenant as any)[key] ?? "");
  },
});

// Methods
const fetchTenants = async () => {
  loading.value = true;
  try {
    const response = await tenantsApi.list({
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      search: searchQuery.value || undefined,
      status: statusFilter.value || undefined,
    });
    tenants.value = response.data.results || response.data;
    pagination.value.total = response.data.count || tenants.value.length;
  } catch (error) {
    console.error("Failed to fetch tenants:", error);
    showToast(t("common.error"), "error");
  } finally {
    loading.value = false;
  }
};

const debouncedSearch = () => {
  if (searchTimeout.value) clearTimeout(searchTimeout.value);
  searchTimeout.value = window.setTimeout(() => {
    pagination.value.page = 1;
    fetchTenants();
  }, 300);
};

const prevPage = () => {
  if (pagination.value.page > 1) {
    pagination.value.page--;
    fetchTenants();
  }
};

const nextPage = () => {
  if (pagination.value.page < totalPages.value) {
    pagination.value.page++;
    fetchTenants();
  }
};

const goToPage = (page: number) => {
  pagination.value.page = page;
  fetchTenants();
};

const handlePageSizeChange = (newSize: number) => {
  pagination.value.pageSize = newSize;
  pagination.value.page = 1;
  fetchTenants();
};

const openCreateDialog = () => {
  editingTenant.value = null;
  formData.value = {
    name: "",
    slug: "",
    description: "",
    contact_email: "",
    max_users: null,
    max_proxies: null,
    max_repositories: null,
    max_storage_gb: null,
  };
  showDialog.value = true;
};

const openEditDialog = (tenant: Tenant) => {
  editingTenant.value = tenant;
  formData.value = {
    name: tenant.name,
    slug: tenant.slug,
    description: tenant.description || "",
    contact_email: tenant.contact_email || "",
    max_users: tenant.max_users,
    max_proxies: tenant.max_proxies,
    max_repositories: tenant.max_repositories,
    max_storage_gb: tenant.max_storage_gb,
  };
  showDialog.value = true;
};

const closeDialog = () => {
  showDialog.value = false;
  editingTenant.value = null;
};

const saveTenant = async () => {
  saving.value = true;
  try {
    if (editingTenant.value) {
      await tenantsApi.update(editingTenant.value.id, formData.value);
      showToast(t("success.saved"), "success");
    } else {
      await tenantsApi.create(formData.value);
      showToast(t("success.created"), "success");
    }
    closeDialog();
    fetchTenants();
  } catch (error: any) {
    console.error("Failed to save tenant:", error);
    showToast(getApiErrorMessage(error, t("common.error")), "error");
  } finally {
    saving.value = false;
  }
};

const confirmDeleteTenant = (tenant: Tenant) => {
  deletingTenant.value = tenant;
  showDeleteConfirm.value = true;
};

const closeDeleteConfirm = (force = false) => {
  if (deleting.value && !force) return;
  showDeleteConfirm.value = false;
  deletingTenant.value = null;
};

const deleteTenant = async () => {
  if (!deletingTenant.value) return;
  deleting.value = true;
  try {
    await tenantsApi.delete(deletingTenant.value.id);
    showToast(t("success.deleted"), "success");
    closeDeleteConfirm(true);
    fetchTenants();
  } catch (error: any) {
    const message = getApiErrorMessage(error, t("common.error"));
    showToast(message, "error");
  } finally {
    deleting.value = false;
  }
};

const viewTenantStats = async (tenant: Tenant) => {
  statsTenant.value = tenant;
  showStatsDrawer.value = true;
  loadingStats.value = true;
  try {
    const response = await tenantsApi.stats(tenant.id);
    statsData.value = response.data;
  } catch (error) {
    console.error("Failed to fetch stats:", error);
  } finally {
    loadingStats.value = false;
  }
};

const closeStatsDrawer = () => {
  showStatsDrawer.value = false;
  statsTenant.value = null;
  statsData.value = null;
};

const openUsersDialog = async (tenant: Tenant) => {
  usersTenant.value = tenant;
  showUsersDrawer.value = true;
  await fetchTenantUsers(tenant.id);
};

const fetchTenantUsers = async (tenantId: string) => {
  loadingUsers.value = true;
  try {
    const response = await tenantsApi.users(tenantId);
    tenantUsers.value = response.data.results || response.data;
  } catch (error) {
    console.error("Failed to fetch tenant users:", error);
    showToast(t("common.error"), "error");
  } finally {
    loadingUsers.value = false;
  }
};

// Helper functions for user display
const getInitials = (user: any): string => {
  if (user.first_name && user.last_name) {
    return (user.first_name[0] + user.last_name[0]).toUpperCase();
  }
  if (user.first_name) {
    return user.first_name.slice(0, 2).toUpperCase();
  }
  return (user.email || "U").slice(0, 2).toUpperCase();
};

const getDisplayName = (user: any): string => {
  if (user.first_name && user.last_name) {
    return `${user.first_name} ${user.last_name}`;
  }
  if (user.first_name) {
    return user.first_name;
  }
  return user.email?.split("@")[0] || "Unknown User";
};

const closeUsersDrawer = () => {
  showUsersDrawer.value = false;
  usersTenant.value = null;
  tenantUsers.value = [];
  userCandidates.value = [];
  selectedUserCandidates.value = [];
  newUserEmail.value = "";
  newUserRole.value = "member";
  showAddUserForm.value = false;
};

const updateUserRole = async (
  userId: string,
  role: string,
  isSuperuser: boolean,
) => {
  if (!usersTenant.value) return;
  try {
    await tenantsApi.updateUser(usersTenant.value.id, userId, {
      role,
      is_superuser: isSuperuser,
    });
    showToast(t("success.saved"), "success");
    await fetchTenantUsers(usersTenant.value.id);
  } catch (error: any) {
    showToast(getApiErrorMessage(error, t("common.error")), "error");
  }
};

const confirmRemoveUser = (user: any) => {
  removingUser.value = user;
  showRemoveUserConfirm.value = true;
};

const executeRemoveUser = async () => {
  if (!removingUser.value || !usersTenant.value) return;
  try {
    await tenantsApi.removeUser(usersTenant.value.id, removingUser.value.id);
    showToast(t("success.deleted"), "success");
    showRemoveUserConfirm.value = false;
    removingUser.value = null;
    await fetchTenantUsers(usersTenant.value.id);
  } catch (error: any) {
    showToast(getApiErrorMessage(error, t("common.error")), "error");
  }
};

// New user form state
const newUserEmail = ref("");
const newUserRole = ref("member");
const showAddUserForm = ref(false);
const showRemoveUserConfirm = ref(false);
const removingUser = ref<any>(null);

// Current user ID for self-check
const currentUserId = ref<string | null>(null);

const handleAddUser = async () => {
  if (!usersTenant.value || selectedUserCandidates.value.length === 0) return;
  try {
    for (const user of selectedUserCandidates.value) {
      await tenantsApi.addUser(usersTenant.value.id, {
        email: user.email,
        role: newUserRole.value,
        is_superuser: false,
      });
    }
    showToast(t("common.success"), "success");
    newUserEmail.value = "";
    selectedUserCandidates.value = [];
    userCandidates.value = [];
    newUserRole.value = "member";
    showAddUserForm.value = false;
    await fetchTenantUsers(usersTenant.value.id);
  } catch (error: any) {
    showToast(getApiErrorMessage(error, t("common.error")), "error");
  }
};

const searchUserCandidates = (query: string) => {
  if (userCandidateSearchTimeout.value) {
    clearTimeout(userCandidateSearchTimeout.value);
  }
  const search = query.trim();
  if (!usersTenant.value || search.length < 2) {
    userCandidates.value = [];
    loadingUserCandidates.value = false;
    return;
  }

  userCandidates.value = [];
  loadingUserCandidates.value = true;
  userCandidateSearchTimeout.value = window.setTimeout(async () => {
    if (!usersTenant.value) return;
    try {
      const response = await tenantsApi.userCandidates(usersTenant.value.id, {
        search,
      });
      const existingEmails = new Set(
        tenantUsers.value.map((user) => user.email?.toLowerCase()),
      );
      const selectedEmails = new Set(
        selectedUserCandidates.value.map((user) => user.email?.toLowerCase()),
      );
      userCandidates.value = (response.data || []).filter(
        (user: any) =>
          !existingEmails.has(user.email?.toLowerCase()) &&
          !selectedEmails.has(user.email?.toLowerCase()),
      );
    } catch (error) {
      userCandidates.value = [];
      showToast(getApiErrorMessage(error, t("common.error")), "error");
    } finally {
      loadingUserCandidates.value = false;
    }
  }, 250);
};

const selectUserCandidate = (user: any) => {
  const exists = selectedUserCandidates.value.some(
    (candidate) => candidate.id === user.id,
  );
  if (!exists) {
    selectedUserCandidates.value = [...selectedUserCandidates.value, user];
  }
  newUserEmail.value = "";
  userCandidates.value = [];
};

const removeSelectedUserCandidate = (userId: string) => {
  selectedUserCandidates.value = selectedUserCandidates.value.filter(
    (user) => user.id !== userId,
  );
};

const activateTenant = async (tenant: Tenant) => {
  try {
    await tenantsApi.activate(tenant.id);
    showToast(t("common.success"), "success");
    fetchTenants();
  } catch (error) {
    showToast(t("common.error"), "error");
  }
};

const deactivateTenant = async (tenant: Tenant) => {
  try {
    await tenantsApi.deactivate(tenant.id);
    showToast(t("common.success"), "success");
    fetchTenants();
  } catch (error) {
    showToast(t("common.error"), "error");
  }
};

const getStatusClass = (status: string) => {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300";
    case "inactive":
      return "bg-gray-100 text-gray-800";
    case "suspended":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300";
    default:
      return "bg-background-tertiary text-foreground";
  }
};

const formatDate = (date: string) => {
  if (!date) return "-";
  return new Date(date).toLocaleDateString();
};

const formatBytes = (bytes: number) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

onMounted(() => {
  fetchTenants();
  // Get current user ID from auth store
  currentUserId.value = authStore.user?.id || null;
});
</script>
