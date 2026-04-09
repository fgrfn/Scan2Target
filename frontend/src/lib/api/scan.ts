import { apiGet, apiPost } from './client';

export interface ScanProfile {
  id: string;
  name: string;
  description: string | null;
  format: string;
  dpi: number;
  color_mode: string;
  source: string | null;
}

export interface PreviewResponse {
  status: string;
  image: string; // base64-encoded JPEG preview
}

export interface Job {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  job_type: string;
  device_id: string | null;
  target_id: string | null;
  file_path: string | null;
  message: string | null;
  filename_prefix: string | null;
  profile_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ScanRequest {
  device_id: string;
  profile_id: string;
  target_id: string;
  filename_prefix: string;
  webhook_url?: string;
}

export interface BatchRequest {
  device_id: string;
  profile_id: string;
  target_id: string;
  filename_prefix: string;
  page_paths: string[];
}

export interface BatchPageResponse {
  status: string;
  image: string;   // base64 preview
  file_path: string; // server-side TIFF path for combine_batch
}

export function getProfiles(): Promise<ScanProfile[]> {
  return apiGet<ScanProfile[]>('/scan/profiles');
}

export function startScan(req: ScanRequest): Promise<{ job_id: string }> {
  return apiPost<{ job_id: string }>('/scan/start', req);
}

export function listJobs(): Promise<Job[]> {
  return apiGet<Job[]>('/scan/jobs');
}

export function getJob(id: string): Promise<Job> {
  return apiGet<Job>(`/scan/jobs/${id}`);
}

export function cancelJob(id: string): Promise<void> {
  return apiPost<void>(`/scan/jobs/${id}/cancel`);
}

export function previewScan(deviceId: string, profileId: string): Promise<PreviewResponse> {
  return apiPost<PreviewResponse>('/scan/preview', {
    device_id: deviceId,
    profile_id: profileId
  });
}

export function scanBatchPage(deviceId: string, profileId: string): Promise<BatchPageResponse> {
  return apiPost<BatchPageResponse>('/scan/batch-page', {
    device_id: deviceId,
    profile_id: profileId
  });
}

export function startBatch(req: BatchRequest): Promise<{ job_id: string }> {
  return apiPost<{ job_id: string }>('/scan/batch', req);
}
