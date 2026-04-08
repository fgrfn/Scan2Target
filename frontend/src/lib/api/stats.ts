import { apiGet } from './client';

export interface StatsOverview {
  total: number;
  successful: number;
  failed: number;
  success_rate: number;
}

export interface TimelineEntry {
  date: string;
  total: number;
  successful: number;
  failed: number;
}

export interface ScannerStat {
  device_id: string;
  device_name: string;
  total: number;
  successful: number;
}

export interface TargetStat {
  target_id: string;
  target_name: string;
  type: string;
  total: number;
  successful: number;
}

export interface HourlyEntry {
  hour: number;
  count: number;
}

export function getOverview(): Promise<StatsOverview> {
  return apiGet<StatsOverview>('/stats/overview');
}

export function getTimeline(days = 30): Promise<TimelineEntry[]> {
  return apiGet<TimelineEntry[]>(`/stats/timeline?days=${days}`);
}

export function getScannerStats(): Promise<ScannerStat[]> {
  return apiGet<ScannerStat[]>('/stats/scanners');
}

export function getTargetStats(): Promise<TargetStat[]> {
  return apiGet<TargetStat[]>('/stats/targets');
}

export function getHourlyStats(): Promise<HourlyEntry[]> {
  return apiGet<HourlyEntry[]>('/stats/hourly');
}
