import { apiDelete, apiGet, apiPost, apiPut } from './client';

export type TargetType =
  | 'smb'
  | 'sftp'
  | 'email'
  | 'paperless'
  | 'webhook'
  | 'local'
  | 'google_drive'
  | 'dropbox'
  | 'onedrive'
  | 'nextcloud';

export interface Target {
  id: string;
  name: string;
  type: TargetType;
  config: Record<string, unknown>;
  enabled: boolean;
  description: string | null;
  is_favorite: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface TargetIn {
  name: string;
  type: TargetType;
  config: Record<string, unknown>;
  enabled?: boolean;
  description?: string;
  is_favorite?: boolean;
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

export function updateTarget(id: string, req: TargetIn): Promise<Target> {
  return apiPut<Target>(`/targets/${id}`, req);
}

export function deleteTarget(id: string): Promise<void> {
  return apiDelete<void>(`/targets/${id}`);
}

export function testTarget(id: string): Promise<TestResult> {
  return apiPost<TestResult>(`/targets/${id}/test`);
}

export function setTargetFavorite(id: string, isFavorite: boolean): Promise<void> {
  return apiPost<void>(`/targets/${id}/favorite`, { is_favorite: isFavorite });
}

export interface BrowsePathResult {
  root: string;
  current: string;
  parent: string | null;
  items: { name: string; path: string }[];
}

export function browseLocalPath(path?: string): Promise<BrowsePathResult> {
  const params = path ? `?path=${encodeURIComponent(path)}` : '';
  return apiGet<BrowsePathResult>(`/targets/browse-path${params}`);
}
