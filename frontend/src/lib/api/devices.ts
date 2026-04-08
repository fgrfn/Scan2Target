import { apiDelete, apiGet, apiPost } from './client';

export interface Device {
  id: string;
  device_type: string;
  uri: string;
  name: string;
  make: string | null;
  model: string | null;
  connection_type: string | null;
  description: string | null;
  is_active: boolean;
  is_favorite: boolean;
  last_seen: string | null;
  online: boolean | null;
}

export interface DiscoveredDevice {
  uri: string;
  name: string;
  make: string | null;
  model: string | null;
  connection_type: string;
  already_added: boolean;
}

export interface AddDeviceRequest {
  uri: string;
  name: string;
  make?: string;
  model?: string;
  device_type?: string;
  connection_type?: string;
  description?: string;
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

export function removeDevice(id: string): Promise<void> {
  return apiDelete<void>(`/devices/${id}`);
}

export function setDeviceFavorite(id: string, isFavorite: boolean): Promise<void> {
  return apiPost<void>(`/devices/${id}/favorite`, { is_favorite: isFavorite });
}

export function checkDeviceOnline(id: string): Promise<{ online: boolean }> {
  return apiGet<{ online: boolean }>(`/devices/${id}/check`);
}

export function getHealthStatus(): Promise<HealthStatus> {
  return apiGet<HealthStatus>('/devices/health/status');
}
