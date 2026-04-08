import { apiDelete, apiGet, apiPost } from './client';
import type { Job } from './scan';

export function listHistory(): Promise<Job[]> {
  return apiGet<Job[]>('/history');
}

export function clearHistory(): Promise<void> {
  return apiDelete<void>('/history');
}

export function deleteHistoryItem(id: string): Promise<void> {
  return apiDelete<void>(`/history/${id}`);
}

export function cancelHistoryJob(id: string): Promise<void> {
  return apiPost<void>(`/history/${id}/cancel`);
}

export function retryUpload(id: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>(`/history/${id}/retry-upload`);
}
