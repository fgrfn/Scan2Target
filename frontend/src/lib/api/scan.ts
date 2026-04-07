import { apiGet, apiPost } from './client';

export interface ScanProfile {
  id: string;
  name: string;
  description: string | null;
  format: string;
  resolution: number;
  color_mode: string;
  source: string | null;
}

export interface Job {
  id: number;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  device_id: number;
  target_id: number;
  profile_id: string;
  filename_prefix: string;
  file_path: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  device_name?: string;
  target_name?: string;
}

export interface ScanRequest {
  device_id: number;
  profile_id: string;
  target_id: number;
  filename_prefix: string;
  webhook_url?: string;
}

export interface BatchRequest {
  device_id: number;
  profile_id: string;
  target_id: number;
  filename_prefix: string;
  page_paths: string[];
}

export interface PreviewResponse {
  status: string;
  image: string; // base64
}

export function getProfiles(): Promise<ScanProfile[]> {
  return apiGet<ScanProfile[]>('/scan/profiles');
}

export function startScan(req: ScanRequest): Promise<Job> {
  return apiPost<Job>('/scan/start', req);
}

export function listJobs(): Promise<Job[]> {
  return apiGet<Job[]>('/scan/jobs');
}

export function getJob(id: number): Promise<Job> {
  return apiGet<Job>(`/scan/jobs/${id}`);
}

export function cancelJob(id: number): Promise<void> {
  return apiPost<void>(`/scan/jobs/${id}/cancel`);
}

export function previewScan(deviceId: number, profileId: string): Promise<PreviewResponse> {
  return apiPost<PreviewResponse>('/scan/preview', {
    device_id: deviceId,
    profile_id: profileId
  });
}

export function startBatch(req: BatchRequest): Promise<Job> {
  return apiPost<Job>('/scan/batch', req);
}
