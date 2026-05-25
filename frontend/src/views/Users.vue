<template>
  <div class="space-y-6">
    <UserToolbar
      v-model:search-query="searchQuery"
      v-model:role-filter="roleFilter"
      v-model:status-filter="statusFilter"
      @search="debouncedSearch"
      @filter="fetchUsers"
      @invite="openInviteDialog"
      @create="openCreateDialog"
    />

    <UserList
      :loading="loading"
      :users="users"
      :user-columns="userColumns"
      :users-table="usersTable"
      :is-platform-admin="Boolean(isPlatformAdmin)"
      :current-user-id="currentUserId"
      :total-count="totalCount"
      :page-size="pageSize"
      :current-page="currentPage"
      :visible-pages="visiblePages"
      :get-initials="getInitials"
      :get-unified-role-class="getUnifiedRoleClass"
      :get-unified-role-name="getUnifiedRoleName"
      :format-date="formatDate"
      @edit="openEditDialog"
      @reset-password="openResetPasswordDialog"
      @toggle-superuser="toggleSuperuser"
      @toggle-status="toggleUserStatus"
      @delete="openDeleteDialog"
      @page="goToPage"
      @pageSizeChange="handlePageSizeChange"
    />

    <UserDialogs
      :show-create-dialog="showCreateDialog"
      :creating="creating"
      :create-form="createForm"
      :tenants="tenants"
      :loading-tenants="loadingTenants"
      :is-platform-admin="Boolean(isPlatformAdmin)"
      :show-edit-dialog="showEditDialog"
      :updating="updating"
      :editing-user="editingUser"
      :edit-form="editForm"
      :show-invite-dialog="showInviteDialog"
      :inviting="inviting"
      :invite-form="inviteForm"
      :show-reset-password-dialog="showResetPasswordDialog"
      :resetting="resetting"
      :resetting-user="resettingUser"
      :reset-password-form="resetPasswordForm"
      :show-delete-dialog="showDeleteDialog"
      :deleting="deleting"
      :deleting-user="deletingUser"
      @close-create="closeCreateDialog"
      @create="createUser"
      @close-edit="closeEditDialog"
      @update="updateUser"
      @close-invite="closeInviteDialog"
      @invite="sendInvite"
      @close-reset-password="closeResetPasswordDialog"
      @reset-password="resetPassword"
      @close-delete="closeDeleteDialog"
      @delete="deleteUser"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";
import { usersApi, invitationsApi, tenantsApi } from "@/api";
import { usePagination } from "@/composables/usePagination";
import { useResizableSortableTable } from "@/composables/useResizableSortableTable";
import { useUserFormatting } from "@/features/users/useUserFormatting";
import UserDialogs from "@/components/users/UserDialogs.vue";
import UserList from "@/components/users/UserList.vue";
import UserToolbar from "@/components/users/UserToolbar.vue";

const { t } = useI18n();
const appStore = useAppStore();
const authStore = useAuthStore();
const { getPageSize, setPageSize } = usePagination();
const { getInitials, getUnifiedRoleName, getUnifiedRoleClass, formatDate } =
  useUserFormatting(t);

interface User {
  id: string;
  email: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  tenant_role: string;
  tenant_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login_at?: string;
  date_joined?: string;
}

const loading = ref(false);
const users = ref<User[]>([]);
const searchQuery = ref("");
const roleFilter = ref("");
const statusFilter = ref("");

// Pagination
const currentPage = ref(1);
const pageSize = ref(getPageSize("users"));
const PAGE_STORAGE_KEY = "users";
const totalCount = ref(0);

// Watch for page size changes and save to localStorage
watch(pageSize, (newSize) => {
  setPageSize(newSize, PAGE_STORAGE_KEY);
});

// Computed
const isPlatformAdmin = computed(() => authStore.user?.is_superuser);
const currentUserId = computed(() => authStore.user?.id);

const visiblePages = computed(() => {
  const totalPages = Math.ceil(totalCount.value / pageSize.value);
  const pages: number[] = [];
  const start = Math.max(1, currentPage.value - 2);
  const end = Math.min(totalPages, currentPage.value + 2);
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  return pages;
});

type UserColumnKey =
  | "user"
  | "email"
  | "tenant_name"
  | "role"
  | "status"
  | "last_login_at"
  | "actions";

const userColumns = computed(() => [
  { key: "user" as const, label: t("users.user"), min: 260, max: 620 },
  { key: "email" as const, label: t("users.email"), min: 240, max: 520 },
  ...(isPlatformAdmin.value
    ? [
        {
          key: "tenant_name" as const,
          label: t("users.tenant"),
          min: 180,
          max: 360,
        },
      ]
    : []),
  { key: "role" as const, label: t("users.role"), min: 140, max: 260 },
  { key: "status" as const, label: t("users.status"), min: 130, max: 240 },
  {
    key: "last_login_at" as const,
    label: t("users.lastLogin"),
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

const usersTable = useResizableSortableTable<User, UserColumnKey>({
  storageKey: "hyperfilelens:users:columnWidths",
  columns: userColumns,
  rows: users,
  defaultSort: { key: "user" },
  minTableWidth: 980,
  getSortValue: (user, key) => {
    if (key === "user") return user.full_name || user.email.split("@")[0] || "";
    if (key === "role") return getUnifiedRoleName(user);
    if (key === "status") return user.is_active ? 1 : 0;
    if (key === "last_login_at")
      return user.last_login_at ? new Date(user.last_login_at).getTime() : 0;
    if (key === "actions") return "";
    return user[key] ?? "";
  },
  getColumnText: (user, key) => {
    if (key === "user") return user.full_name || user.email.split("@")[0] || "";
    if (key === "role") return getUnifiedRoleName(user);
    if (key === "status")
      return user.is_active ? t("users.active") : t("users.inactive");
    if (key === "last_login_at")
      return user.last_login_at ? formatDate(user.last_login_at) : "-";
    if (key === "actions") return t("common.actions");
    return String(user[key] ?? "");
  },
});

// Create dialog
const showCreateDialog = ref(false);
const creating = ref(false);
const createForm = ref({
  email: "",
  password: "",
  first_name: "",
  last_name: "",
  phone: "",
  role: "member", // 统一角色：platform_admin / admin / member
  tenant_id: "",
});

// Tenant list for platform admin
const tenants = ref<{ id: string; name: string }[]>([]);
const loadingTenants = ref(false);

// Edit dialog
const showEditDialog = ref(false);
const updating = ref(false);
const editingUser = ref<User | null>(null);
const editForm = ref({
  email: "",
  first_name: "",
  last_name: "",
  phone: "",
  role: "", // 统一角色：platform_admin / admin / member
});

// Reset password dialog
const showResetPasswordDialog = ref(false);
const resetting = ref(false);
const resettingUser = ref<User | null>(null);
const resetPasswordForm = ref({
  new_password: "",
  confirm_password: "",
});

// Delete dialog
const showDeleteDialog = ref(false);
const deleting = ref(false);
const deletingUser = ref<User | null>(null);

// Invite dialog
const showInviteDialog = ref(false);
const inviting = ref(false);
const inviteForm = ref({
  email: "",
  role: "member",
});

// Debounce
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(fetchUsers, 300);
};

async function fetchUsers() {
  loading.value = true;
  try {
    const params: {
      page: number;
      page_size: number;
      search?: string;
      tenant_role?: string;
      is_active?: boolean;
    } = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (searchQuery.value) params.search = searchQuery.value;
    if (roleFilter.value) params.tenant_role = roleFilter.value;
    if (statusFilter.value) params.is_active = statusFilter.value === "active";

    const response = await usersApi.list(params);
    users.value = response.data.results || response.data;
    totalCount.value = response.data.count || users.value.length;
  } catch (error: unknown) {
    console.error("Failed to fetch users:", error);
    appStore.showToast({ type: "error", title: t("common.error") });
  } finally {
    loading.value = false;
  }
}

function goToPage(page: number) {
  if (page < 1 || page > Math.ceil(totalCount.value / pageSize.value)) return;
  currentPage.value = page;
  fetchUsers();
}

function handlePageSizeChange(newSize: number) {
  pageSize.value = newSize;
  currentPage.value = 1;
  fetchUsers();
}

// Create
async function openCreateDialog() {
  createForm.value = {
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
    role: "member",
    tenant_id: "",
  };
  showCreateDialog.value = true;

  // Fetch tenants for platform admin
  if (isPlatformAdmin.value && tenants.value.length === 0) {
    loadingTenants.value = true;
    try {
      const response = await tenantsApi.list({ page_size: 100 });
      tenants.value = response.data.results || response.data;
    } catch (error) {
      console.error("Failed to fetch tenants:", error);
    } finally {
      loadingTenants.value = false;
    }
  }
}

function closeCreateDialog() {
  showCreateDialog.value = false;
}

async function createUser() {
  creating.value = true;
  try {
    // 将统一角色转换为后端字段
    const role = createForm.value.role;
    const is_superuser = role === "platform_admin";
    const tenant_role = role === "platform_admin" ? "admin" : role;

    const payload = {
      email: createForm.value.email,
      password: createForm.value.password,
      first_name: createForm.value.first_name,
      last_name: createForm.value.last_name,
      phone: createForm.value.phone,
      tenant_role,
      is_superuser,
      tenant_id: createForm.value.tenant_id || undefined,
    };
    await usersApi.create(payload);
    appStore.showToast({ type: "success", title: t("users.createSuccess") });
    closeCreateDialog();
    fetchUsers();
  } catch (error: unknown) {
    const err = error as {
      response?: { data?: { detail?: string; error?: string; field?: string } };
    };
    const errorMsg = err.response?.data?.detail || err.response?.data?.error;
    if (
      errorMsg?.includes("email already exists") ||
      err.response?.data?.field === "email"
    ) {
      appStore.showToast({ type: "error", title: t("users.emailExists") });
    } else {
      appStore.showToast({
        type: "error",
        title: errorMsg || t("users.createFailed"),
      });
    }
  } finally {
    creating.value = false;
  }
}

// Edit
function openEditDialog(user: User) {
  editingUser.value = user;
  // 根据用户的 is_superuser 和 tenant_role 确定统一角色
  let role = "member";
  if (user.is_superuser) {
    role = "platform_admin";
  } else if (user.tenant_role === "admin") {
    role = "admin";
  }
  editForm.value = {
    email: user.email || "",
    first_name: user.first_name || "",
    last_name: user.last_name || "",
    phone: user.phone || "",
    role: role,
  };
  showEditDialog.value = true;
}

function closeEditDialog() {
  showEditDialog.value = false;
  editingUser.value = null;
}

async function updateUser() {
  if (!editingUser.value) return;
  updating.value = true;
  try {
    // Update basic info (including email)
    await usersApi.update(String(editingUser.value.id), {
      email: editForm.value.email,
      first_name: editForm.value.first_name,
      last_name: editForm.value.last_name,
      phone: editForm.value.phone,
    });

    // Calculate new role values
    const newRole = editForm.value.role;
    const newIsSuperuser = newRole === "platform_admin";
    const newTenantRole = newRole === "platform_admin" ? "admin" : newRole;

    // Update superuser status if changed
    if (newIsSuperuser !== editingUser.value.is_superuser) {
      await usersApi.setSuperuser(String(editingUser.value.id), newIsSuperuser);
    }

    // Update tenant role if changed
    if (newTenantRole !== editingUser.value.tenant_role) {
      await usersApi.changeRole(String(editingUser.value.id), newTenantRole);
    }

    appStore.showToast({ type: "success", title: t("users.updateSuccess") });
    closeEditDialog();
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.updateFailed"),
    });
  } finally {
    updating.value = false;
  }
}

// Toggle superuser
async function toggleSuperuser(user: User, isSuperuser: boolean) {
  try {
    await usersApi.setSuperuser(user.id, isSuperuser);
    appStore.showToast({
      type: "success",
      title: isSuperuser
        ? t("users.setPlatformAdmin")
        : t("users.removePlatformAdmin"),
    });
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("common.error"),
    });
  }
}

// Invite
function openInviteDialog() {
  inviteForm.value = { email: "", role: "member" };
  showInviteDialog.value = true;
}

function closeInviteDialog() {
  showInviteDialog.value = false;
}

async function sendInvite() {
  inviting.value = true;
  try {
    await invitationsApi.create(inviteForm.value);
    appStore.showToast({ type: "success", title: t("users.inviteSuccess") });
    closeInviteDialog();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.inviteFailed"),
    });
  } finally {
    inviting.value = false;
  }
}

// Toggle status
async function toggleUserStatus(user: User, active: boolean) {
  try {
    if (active) {
      await usersApi.enable(user.id);
    } else {
      await usersApi.disable(user.id);
    }
    appStore.showToast({
      type: "success",
      title: active ? t("users.enableSuccess") : t("users.disableSuccess"),
    });
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("common.error"),
    });
  }
}

// Reset password
function openResetPasswordDialog(user: User) {
  resettingUser.value = user;
  resetPasswordForm.value = { new_password: "", confirm_password: "" };
  showResetPasswordDialog.value = true;
}

function closeResetPasswordDialog() {
  showResetPasswordDialog.value = false;
  resettingUser.value = null;
}

async function resetPassword() {
  if (!resettingUser.value) return;

  if (!resetPasswordForm.value.new_password) {
    appStore.showToast({ type: "error", title: t("users.passwordRequired") });
    return;
  }

  if (resetPasswordForm.value.new_password.length < 6) {
    appStore.showToast({ type: "error", title: t("users.passwordTooShort") });
    return;
  }

  if (
    resetPasswordForm.value.new_password !==
    resetPasswordForm.value.confirm_password
  ) {
    appStore.showToast({ type: "error", title: t("users.passwordMismatch") });
    return;
  }

  resetting.value = true;
  try {
    await usersApi.resetPassword(
      String(resettingUser.value.id),
      resetPasswordForm.value.new_password,
    );
    appStore.showToast({
      type: "success",
      title: t("users.resetPasswordSuccess"),
    });
    closeResetPasswordDialog();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.resetPasswordFailed"),
    });
  } finally {
    resetting.value = false;
  }
}

// Delete user
function openDeleteDialog(user: User) {
  deletingUser.value = user;
  showDeleteDialog.value = true;
}

function closeDeleteDialog() {
  showDeleteDialog.value = false;
  deletingUser.value = null;
}

async function deleteUser() {
  if (!deletingUser.value) return;

  deleting.value = true;
  try {
    await usersApi.delete(String(deletingUser.value.id));
    appStore.showToast({ type: "success", title: t("users.deleteSuccess") });
    closeDeleteDialog();
    fetchUsers();
  } catch (error: unknown) {
    const err = error as { response?: { data?: { error?: string } } };
    appStore.showToast({
      type: "error",
      title: err.response?.data?.error || t("users.deleteFailed"),
    });
  } finally {
    deleting.value = false;
  }
}

onMounted(() => {
  fetchUsers();
});
</script>
