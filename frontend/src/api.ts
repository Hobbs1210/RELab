const TOKEN_KEY = 'relab_admin_token';

export function getAdminToken(): string {
  return sessionStorage.getItem(TOKEN_KEY) || '';
}

export function setAdminToken(token: string): void {
  if (token) {
    sessionStorage.setItem(TOKEN_KEY, token);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export async function labFetch<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    let token = getAdminToken();
    if (!token) {
      const prompted = window.prompt('Enter LAB_ADMIN_TOKEN from .env (stored only in this browser session):');
      if (prompted) {
        token = prompted.trim();
        setAdminToken(token);
      }
    }
    if (token) {
      headers.set('X-Lab-Token', token);
    }
  }

  const res = await fetch(`/__lab__/${path.replace(/^\//, '')}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errMsg = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      errMsg = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      // fallback
    }
    throw new Error(errMsg);
  }

  // Handle binary / text responses if requested
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json() as Promise<T>;
  }
  return res.text() as Promise<T>;
}
