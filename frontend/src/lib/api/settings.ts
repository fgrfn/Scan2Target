import { apiGet, apiPut } from './client';

export interface AppSettings {
  require_auth: boolean;
  log_level: string;
  health_check_interval: number;
  scanner_check_interval: number;
  command_timeout: number;
  cors_origins: string[];
}

export function getSettings(): Promise<AppSettings> {
  return apiGet<AppSettings>('/settings');
}

export function updateSetting(key: string, value: unknown): Promise<void> {
  return apiPut<void>(`/settings/${key}`, { value });
}
