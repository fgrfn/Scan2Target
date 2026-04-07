import { apiDelete, apiGet, apiPost } from './client';

export interface Device {
  id: number;
  uri: string;
  name: string;
  model: string | null;
  manufacturer: string | null;
  is_favorite: boolean;
  is_online: boolean | null;
  last_checked: string | null;
  created_at: string;
}

export interface DiscoveredDevice {
  uri: string;
  name: string;
  model: string | null;
  manufacturer: string | null;
}

export interface AddDeviceRequest {
  uri: string;
  name: string;
  model?: string;
  manufacturer?: string;
}

export interface HealthStatus {
  [deviceId: string]: boolean;
}

export function listDevices(): Promise<Device[]> {
  return apiGet<Device[]>('/devices');
}

export function discoverDevices(): Promise<DiscoveredDevice[]> {
  return apiGet<DiscoveredDevice[]>('/devices/discover');
}

export function addDevice(req: AddDeviceRequest): Promise<Device> {
  return apiPost<Device>('/devices', req);
}

export function removeDevice(id: number): Promise<void> {
  return apiDelete<void>(`/devices/${id}`);
}

export function setDeviceFavorite(id: number, isFavorite: boolean): Promise<void> {
  return apiPost<void>(`/devices/${id}/favorite`, { is_favorite: isFavorite });
}

export function checkDeviceOnline(id: number): Promise<{ online: boolean }> {
  return apiGet<{ online: boolean }>(`/devices/${id}/check`);
}

export function getHealthStatus(): Promise<HealthStatus> {
  return apiGet<HealthStatus>('/devices/health/status');
}
