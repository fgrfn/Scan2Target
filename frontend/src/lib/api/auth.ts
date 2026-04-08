import { apiGet, apiPost } from './client';

export interface User {
  id: number;
  username: string;
  email: string | null;
  is_admin: boolean;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export function getAuthConfig(): Promise<{ require_auth: boolean }> {
  return apiGet<{ require_auth: boolean }>('/auth/config');
}

export function login(username: string, password: string): Promise<TokenResponse> {
  return apiPost<TokenResponse>('/auth/login', { username, password });
}

export function logout(): Promise<void> {
  return apiPost<void>('/auth/logout');
}

export function getMe(): Promise<User> {
  return apiGet<User>('/auth/me');
}
