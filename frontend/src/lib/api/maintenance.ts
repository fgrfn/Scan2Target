import { apiGet, apiPost } from './client';

export interface DiskUsage {
  total_bytes: number;
  used_bytes: number;
  total_mb: number;
  breakdown: {
    thumbnails: number;
    pdfs: number;
    images: number;
    other: number;
  };
}

export interface CleanupResult {
  deleted_thumbnails: number;
  deleted_files: number;
}

export function runCleanup(): Promise<CleanupResult> {
  return apiPost<CleanupResult>('/maintenance/cleanup');
}

export function getDiskUsage(): Promise<DiskUsage> {
  return apiGet<DiskUsage>('/maintenance/disk-usage');
}
