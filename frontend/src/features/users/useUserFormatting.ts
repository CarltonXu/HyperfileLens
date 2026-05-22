type Translate = (key: string, params?: Record<string, any>) => string;

interface User {
  email: string;
  full_name?: string;
  first_name?: string;
  last_name?: string;
  tenant_role: string;
  is_superuser: boolean;
}

export function useUserFormatting(t: Translate) {
  function getInitials(user: User) {
    if (user.full_name) {
      return user.full_name
        .split(" ")
        .map((name: string) => name[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    if (user.first_name && user.last_name) {
      return (user.first_name[0] + user.last_name[0]).toUpperCase();
    }
    return (user.email || "U").slice(0, 2).toUpperCase();
  }

  function getUnifiedRoleName(user: User) {
    if (user.is_superuser) {
      return t("users.roles.platformAdmin");
    }
    if (user.tenant_role === "admin") {
      return t("users.roles.tenantAdmin");
    }
    return t("users.roles.member");
  }

  function getUnifiedRoleClass(user: User) {
    if (user.is_superuser) {
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
    }
    if (user.tenant_role === "admin") {
      return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200";
    }
    return "bg-gray-100 text-gray-800";
  }

  function formatDate(date: string) {
    if (!date) return "-";
    return new Date(date).toLocaleDateString();
  }

  return {
    getInitials,
    getUnifiedRoleName,
    getUnifiedRoleClass,
    formatDate,
  };
}
