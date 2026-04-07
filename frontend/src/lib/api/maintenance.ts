import { apiGet, apiPost } from './client';

export interface DiskUsage {
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  scan_dir_bytes: number;
}

export interface CleanupResult {
  deleted_files: number;
  freed_bytes: number;
}

export function runCleanup(): Promise<CleanupResult> {
  return apiPost<CleanupResult>('/maintenance/cleanup');
}

export function getDiskUsage(): Promise<DiskUsage> {
  return apiGet<DiskUsage>('/maintenance/disk-usage');
}
