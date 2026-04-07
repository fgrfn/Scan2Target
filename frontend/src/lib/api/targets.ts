import { apiDelete, apiGet, apiPost, apiPut } from './client';

export type TargetType =
  | 'smb'
  | 'sftp'
  | 'email'
  | 'paperless'
  | 'webhook'
  | 'google_drive'
  | 'dropbox'
  | 'onedrive'
  | 'nextcloud';

export interface Target {
  id: number;
  name: string;
  type: TargetType;
  connection: string | null;
  username: string | null;
  is_favorite: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  config: Record<string, unknown>;
}

export interface TargetIn {
  name: string;
  type: TargetType;
  connection?: string;
  username?: string;
  password?: string;
  config?: Record<string, unknown>;
}

export interface TestResult {
  success: boolean;
  message: string;
}

export function listTargets(): Promise<Target[]> {
  return apiGet<Target[]>('/targets');
}

export function createTarget(req: TargetIn): Promise<Target> {
  return apiPost<Target>('/targets', req);
}

export function updateTarget(id: number, req: TargetIn): Promise<Target> {
  return apiPut<Target>(`/targets/${id}`, req);
}

export function deleteTarget(id: number): Promise<void> {
  return apiDelete<void>(`/targets/${id}`);
}

export function testTarget(id: number): Promise<TestResult> {
  return apiPost<TestResult>(`/targets/${id}/test`);
}

export function setTargetFavorite(id: number, isFavorite: boolean): Promise<void> {
  return apiPost<void>(`/targets/${id}/favorite`, { is_favorite: isFavorite });
}
