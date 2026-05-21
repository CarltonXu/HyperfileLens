export interface NotificationChannel {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface NotificationChannelTestResult {
  success: boolean;
  message?: string;
}
