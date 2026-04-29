/**
 * Tenant types for multi-tenancy support
 */

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: 'free' | 'basic' | 'pro' | 'enterprise';
  status: 'active' | 'suspended' | 'trial';
  max_proxies: number;
  max_repositories: number;
  max_storage_gb: number;
  max_users: number;
  max_backup_tasks: number;
  contact_email: string;
  contact_phone?: string;
  logo_url?: string;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  trial_ends_at?: string;
  subscription_ends_at?: string;
  // Additional fields from API
  description?: string;
  owner_name?: string;
  owner_email?: string;
  user_count?: number;
  proxy_count?: number;
  repository_count?: number;
  storage_used?: number;
}

export interface TenantQuotaUsage {
  proxies: number;
  repositories: number;
  users: number;
  storage_used_gb: number;
}

export interface TenantWithUsage extends Tenant {
  quota_usage: TenantQuotaUsage;
  is_within_quota: boolean;
}

export interface TenantInvitation {
  id: string;
  tenant: string;
  tenant_name: string;
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  invited_by: string;
  invited_by_name: string;
  status: 'pending' | 'accepted' | 'declined' | 'expired';
  created_at: string;
  expires_at: string;
  accepted_at?: string;
}

export interface CreateTenantRequest {
  name: string;
  slug: string;
  plan?: string;
  contact_email?: string;
  contact_phone?: string;
  max_proxies?: number;
  max_repositories?: number;
  max_storage_gb?: number;
  max_users?: number;
  description?: string;
}

export interface CreateInvitationRequest {
  email: string;
  role: string;
}

export type TenantRole = 'owner' | 'admin' | 'member' | 'viewer';
