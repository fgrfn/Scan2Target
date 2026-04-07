const BASE = '/api/v1';

function getToken(): string | null {
  return localStorage.getItem('token');
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined)
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(`${BASE}${path}`, {
    ...options,
    headers
  });

  if (!resp.ok) {
    let message = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      message = body?.detail ?? body?.message ?? message;
    } catch {
      // ignore parse error
    }
    throw new ApiError(resp.status, message);
  }

  // Handle empty body (204 No Content etc.)
  const contentType = resp.headers.get('content-type') ?? '';
  if (resp.status === 204 || !contentType.includes('application/json')) {
    return undefined as T;
  }

  return resp.json() as Promise<T>;
}

export function apiGet<T = unknown>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: 'GET' });
}

export function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined
  });
}

export function apiPut<T = unknown>(path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'PUT',
    body: body !== undefined ? JSON.stringify(body) : undefined
  });
}

export function apiDelete<T = unknown>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: 'DELETE' });
}
