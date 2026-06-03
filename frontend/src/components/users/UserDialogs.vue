<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ExclamationTriangleIcon } from "@heroicons/vue/24/outline";

interface User {
  id: string;
  email: string;
  full_name?: string;
}

interface TenantOption {
  id: string;
  name: string;
}

interface UserCreateForm {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone: string;
  tenant_id: string;
  role: string;
}

interface UserEditForm {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: string;
}

interface InviteForm {
  email: string;
  role: string;
  tenant_id: string;
}

interface ResetPasswordForm {
  new_password: string;
  confirm_password: string;
}

interface JoinTenantForm {
  tenant_id: string;
  role: string;
}

defineProps<{
  showCreateDialog: boolean;
  creating: boolean;
  createForm: UserCreateForm;
  tenants: TenantOption[];
  loadingTenants: boolean;
  isPlatformAdmin: boolean;
  showEditDialog: boolean;
  updating: boolean;
  editingUser: User | null;
  editForm: UserEditForm;
  showInviteDialog: boolean;
  inviting: boolean;
  inviteForm: InviteForm;
  showResetPasswordDialog: boolean;
  resetting: boolean;
  resettingUser: User | null;
  resetPasswordForm: ResetPasswordForm;
  showJoinTenantDialog: boolean;
  joiningTenant: boolean;
  joiningUser: User | null;
  joinTenantForm: JoinTenantForm;
  showDeleteDialog: boolean;
  deleting: boolean;
  deletingUser: User | null;
}>();

const emit = defineEmits<{
  closeCreate: [];
  create: [];
  closeEdit: [];
  update: [];
  closeInvite: [];
  invite: [];
  closeResetPassword: [];
  resetPassword: [];
  closeJoinTenant: [];
  joinTenant: [];
  closeDelete: [];
  delete: [];
}>();

const { t } = useI18n();
</script>

<template>
  <Teleport to="body">
    <div v-if="showCreateDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div
        class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
      >
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="emit('closeCreate')"
        />
        <div
          class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
        >
          <div class="mt-3 text-center sm:mt-5">
            <h3 class="text-base font-semibold leading-6 text-foreground">
              {{ t("users.createUser") }}
            </h3>
            <div class="mt-4 space-y-4 text-left">
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.email") }} *</label
                >
                <input
                  v-model="createForm.email"
                  type="email"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  :placeholder="t('users.emailPlaceholder')"
                />
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.password") }} *</label
                >
                <input
                  v-model="createForm.password"
                  type="password"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  :placeholder="t('users.passwordPlaceholder')"
                />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label
                    class="block text-sm font-medium text-foreground-secondary"
                    >{{ t("users.firstName") }}</label
                  >
                  <input
                    v-model="createForm.first_name"
                    type="text"
                    class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  />
                </div>
                <div>
                  <label
                    class="block text-sm font-medium text-foreground-secondary"
                    >{{ t("users.lastName") }}</label
                  >
                  <input
                    v-model="createForm.last_name"
                    type="text"
                    class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  />
                </div>
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.phone") }}</label
                >
                <input
                  v-model="createForm.phone"
                  type="text"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
              <div v-if="isPlatformAdmin">
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.tenant") }}</label
                >
                <select
                  v-model="createForm.tenant_id"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                  :disabled="loadingTenants"
                >
                  <option class="bg-background" value="">
                    {{
                      loadingTenants
                        ? t("common.loading")
                        : t("users.selectTenant")
                    }}
                  </option>
                  <option
                    v-for="tenant in tenants"
                    :key="tenant.id"
                    class="bg-background"
                    :value="tenant.id"
                  >
                    {{ tenant.name }}
                  </option>
                </select>
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.role") }}</label
                >
                <select
                  v-model="createForm.role"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                >
                  <option
                    v-if="isPlatformAdmin"
                    class="bg-background"
                    value="platform_admin"
                  >
                    {{ t("users.roles.platformAdmin") }}
                  </option>
                  <option class="bg-background" value="admin">
                    {{ t("users.roles.tenantAdmin") }}
                  </option>
                  <option class="bg-background" value="member">
                    {{ t("users.roles.member") }}
                  </option>
                </select>
              </div>
            </div>
          </div>
          <div
            class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3"
          >
            <button
              type="button"
              class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:col-start-2"
              :disabled="creating"
              @click="emit('create')"
            >
              {{ creating ? t("common.saving") : t("common.save") }}
            </button>
            <button
              type="button"
              class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
              @click="emit('closeCreate')"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div v-if="showEditDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div
        class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
      >
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="emit('closeEdit')"
        />
        <div
          class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
        >
          <div class="mt-3 text-center sm:mt-5">
            <h3 class="text-base font-semibold leading-6 text-foreground">
              {{ t("users.editUser") }}
            </h3>
            <p class="mt-2 text-sm text-foreground-secondary">
              {{
                t("users.editUserHint", {
                  user: editingUser?.full_name || editingUser?.email,
                })
              }}
            </p>
            <div class="mt-4 space-y-4 text-left">
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.email") }}</label
                >
                <input
                  v-model="editForm.email"
                  type="email"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label
                    class="block text-sm font-medium text-foreground-secondary"
                    >{{ t("users.firstName") }}</label
                  >
                  <input
                    v-model="editForm.first_name"
                    type="text"
                    class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  />
                </div>
                <div>
                  <label
                    class="block text-sm font-medium text-foreground-secondary"
                    >{{ t("users.lastName") }}</label
                  >
                  <input
                    v-model="editForm.last_name"
                    type="text"
                    class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  />
                </div>
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.phone") }}</label
                >
                <input
                  v-model="editForm.phone"
                  type="text"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.role") }}</label
                >
                <select
                  v-model="editForm.role"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                >
                  <option
                    v-if="isPlatformAdmin"
                    class="bg-background"
                    value="platform_admin"
                  >
                    {{ t("users.roles.platformAdmin") }}
                  </option>
                  <option class="bg-background" value="admin">
                    {{ t("users.roles.tenantAdmin") }}
                  </option>
                  <option class="bg-background" value="member">
                    {{ t("users.roles.member") }}
                  </option>
                </select>
              </div>
            </div>
          </div>
          <div
            class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3"
          >
            <button
              type="button"
              class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:col-start-2"
              :disabled="updating"
              @click="emit('update')"
            >
              {{ updating ? t("common.saving") : t("users.updateUser") }}
            </button>
            <button
              type="button"
              class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
              @click="emit('closeEdit')"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div v-if="showInviteDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div
        class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
      >
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="emit('closeInvite')"
        />
        <div
          class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
        >
          <div class="mt-3 text-center sm:mt-5">
            <h3 class="text-base font-semibold leading-6 text-foreground">
              {{ t("users.inviteUser") }}
            </h3>
            <div class="mt-4 space-y-4 text-left">
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.email") }}</label
                >
                <input
                  v-model="inviteForm.email"
                  type="email"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  :placeholder="t('users.emailPlaceholder')"
                />
              </div>
              <div v-if="isPlatformAdmin">
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.tenant") }} *</label
                >
                <select
                  v-model="inviteForm.tenant_id"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                  :disabled="loadingTenants"
                >
                  <option class="bg-background" value="">
                    {{
                      loadingTenants
                        ? t("common.loading")
                        : t("users.selectTenant")
                    }}
                  </option>
                  <option
                    v-for="tenant in tenants"
                    :key="tenant.id"
                    class="bg-background"
                    :value="tenant.id"
                  >
                    {{ tenant.name }}
                  </option>
                </select>
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.role") }}</label
                >
                <select
                  v-model="inviteForm.role"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                >
                  <option class="bg-background" value="admin">
                    {{ t("users.roles.admin") }}
                  </option>
                  <option class="bg-background" value="member">
                    {{ t("users.roles.member") }}
                  </option>
                </select>
              </div>
            </div>
          </div>
          <div
            class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3"
          >
            <button
              type="button"
              class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:col-start-2"
              :disabled="
                inviting ||
                (isPlatformAdmin && !inviteForm.tenant_id) ||
                loadingTenants
              "
              @click="emit('invite')"
            >
              {{ inviting ? t("users.sending") : t("users.sendInvite") }}
            </button>
            <button
              type="button"
              class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
              @click="emit('closeInvite')"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div
      v-if="showResetPasswordDialog"
      class="fixed inset-0 z-50 overflow-y-auto"
    >
      <div
        class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
      >
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="emit('closeResetPassword')"
        />
        <div
          class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
        >
          <div class="mt-3 text-center sm:mt-5">
            <h3 class="text-base font-semibold leading-6 text-foreground">
              {{ t("users.resetPassword") }}
            </h3>
            <p class="mt-2 text-sm text-foreground-secondary">
              {{ t("users.resetPasswordFor") }}: {{ resettingUser?.email }}
            </p>
            <div class="mt-4 space-y-4 text-left">
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.newPassword") }} *</label
                >
                <input
                  v-model="resetPasswordForm.new_password"
                  type="password"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  :placeholder="t('users.passwordPlaceholder')"
                />
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.confirmPassword") }} *</label
                >
                <input
                  v-model="resetPasswordForm.confirm_password"
                  type="password"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground placeholder:text-foreground-muted focus:ring-2 focus:ring-indigo-500 text-sm"
                  :placeholder="t('users.confirmPasswordPlaceholder')"
                />
              </div>
            </div>
          </div>
          <div
            class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3"
          >
            <button
              type="button"
              class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 sm:col-start-2"
              :disabled="resetting"
              @click="emit('resetPassword')"
            >
              {{ resetting ? t("common.saving") : t("users.resetPassword") }}
            </button>
            <button
              type="button"
              class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
              @click="emit('closeResetPassword')"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div v-if="showJoinTenantDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div
        class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
      >
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="emit('closeJoinTenant')"
        />
        <div
          class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
        >
          <div class="mt-3 text-center sm:mt-5">
            <h3 class="text-base font-semibold leading-6 text-foreground">
              {{ t("users.joinTenant") }}
            </h3>
            <p class="mt-2 text-sm text-foreground-secondary">
              {{
                t("users.joinTenantHint", {
                  user: joiningUser?.full_name || joiningUser?.email,
                })
              }}
            </p>
            <div class="mt-4 space-y-4 text-left">
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.tenant") }} *</label
                >
                <select
                  v-model="joinTenantForm.tenant_id"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                  :disabled="loadingTenants"
                >
                  <option class="bg-background" value="">
                    {{
                      loadingTenants
                        ? t("common.loading")
                        : t("users.selectTenant")
                    }}
                  </option>
                  <option
                    v-for="tenant in tenants"
                    :key="tenant.id"
                    class="bg-background"
                    :value="tenant.id"
                  >
                    {{ tenant.name }}
                  </option>
                </select>
              </div>
              <div>
                <label
                  class="block text-sm font-medium text-foreground-secondary"
                  >{{ t("users.role") }}</label
                >
                <select
                  v-model="joinTenantForm.role"
                  class="mt-1 block w-full rounded-lg border border-border px-3 py-2 bg-background text-foreground focus:ring-2 focus:ring-indigo-500 text-sm"
                >
                  <option class="bg-background" value="admin">
                    {{ t("users.roles.tenantAdmin") }}
                  </option>
                  <option class="bg-background" value="member">
                    {{ t("users.roles.member") }}
                  </option>
                </select>
              </div>
            </div>
          </div>
          <div
            class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3"
          >
            <button
              type="button"
              class="inline-flex w-full justify-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 sm:col-start-2"
              :disabled="joiningTenant || loadingTenants || !joinTenantForm.tenant_id"
              @click="emit('joinTenant')"
            >
              {{ joiningTenant ? t("common.saving") : t("users.joinTenant") }}
            </button>
            <button
              type="button"
              class="mt-3 inline-flex w-full justify-center rounded-lg border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground-secondary hover:bg-hover sm:col-start-1 sm:mt-0 transition-colors"
              @click="emit('closeJoinTenant')"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div v-if="showDeleteDialog" class="fixed inset-0 z-50 overflow-y-auto">
      <div
        class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0"
      >
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          @click="emit('closeDelete')"
        />
        <div
          class="relative transform overflow-hidden rounded-xl modal-surface border border-border px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
        >
          <div class="sm:flex sm:items-start">
            <div
              class="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-900 sm:mx-0 sm:h-10 sm:w-10"
            >
              <ExclamationTriangleIcon
                class="h-6 w-6 text-red-600 dark:text-red-400"
                aria-hidden="true"
              />
            </div>
            <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
              <h3 class="text-base font-semibold leading-6 text-foreground">
                {{ t("users.deleteUser") }}
              </h3>
              <div class="mt-2">
                <p class="text-sm text-foreground-secondary">
                  {{
                    t("users.confirmDeleteDesc", { email: deletingUser?.email })
                  }}
                </p>
              </div>
            </div>
          </div>
          <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              class="inline-flex w-full justify-center rounded-md bg-red-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-500 sm:ml-3 sm:w-auto"
              :disabled="deleting"
              @click="emit('delete')"
            >
              {{ deleting ? t("common.deleting") : t("users.deleteUser") }}
            </button>
            <button
              type="button"
              class="mt-3 inline-flex w-full justify-center rounded-md bg-card px-3 py-2 text-sm font-semibold text-foreground shadow-sm ring-1 ring-inset ring-border hover:bg-hover sm:mt-0 sm:w-auto"
              @click="emit('closeDelete')"
            >
              {{ t("common.cancel") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
