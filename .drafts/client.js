 /**
 * AquaGest API Client
 * JWT auth, auto-refresh, error interception, full CRUD
 */

const API_BASE = '/api';
const TOKEN_KEY = 'aq_access';
const REFRESH_KEY = 'aq_refresh';
const USER_KEY = 'aq_user';

// ─────────────────────────────────────────────
// Token Storage
// ─────────────────────────────────────────────
export const TokenStore = {
  getAccess:  () => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  getUser:    () => { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; } },

  set(access, refresh, user = null) {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    if (user)    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  },

  isAuthenticated() { return !!this.getAccess(); },

  // Decode JWT payload (no verification – just reading claims)
  decodeAccess() {
    const token = this.getAccess();
    if (!token) return null;
    try {
      const payload = token.split('.')[1];
      return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    } catch { return null; }
  },

  isExpired() {
    const payload = this.decodeAccess();
    if (!payload?.exp) return true;
    return Date.now() / 1000 >= payload.exp - 30; // 30s buffer
  }
};

// ─────────────────────────────────────────────
// Refresh queue – prevents multiple concurrent refreshes
// ─────────────────────────────────────────────
let _refreshing = false;
let _refreshQueue = [];

async function refreshAccessToken() {
  const refresh = TokenStore.getRefresh();
  if (!refresh) throw new Error('No refresh token');

  const res = await fetch(`${API_BASE}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });

  if (!res.ok) {
    TokenStore.clear();
    window.dispatchEvent(new CustomEvent('aq:session-expired'));
    throw new Error('Session expired');
  }

  const data = await res.json();
  TokenStore.set(data.access, refresh);
  return data.access;
}

async function getValidToken() {
  if (!TokenStore.isExpired()) return TokenStore.getAccess();

  if (_refreshing) {
    return new Promise((resolve, reject) => {
      _refreshQueue.push({ resolve, reject });
    });
  }

  _refreshing = true;
  try {
    const token = await refreshAccessToken();
    _refreshQueue.forEach(q => q.resolve(token));
    return token;
  } catch (err) {
    _refreshQueue.forEach(q => q.reject(err));
    throw err;
  } finally {
    _refreshing = false;
    _refreshQueue = [];
  }
}

// ─────────────────────────────────────────────
// Core fetch wrapper
// ─────────────────────────────────────────────
async function request(method, endpoint, { body, params, multipart = false } = {}) {
  let url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

  if (params) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ''))
    );
    if (qs.toString()) url += '?' + qs.toString();
  }

  const headers = {};

  if (TokenStore.isAuthenticated()) {
    try {
      const token = await getValidToken();
      headers['Authorization'] = `Bearer ${token}`;
    } catch {
      redirectToLogin();
      return;
    }
  }

  if (!multipart) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };

  if (body) {
    opts.body = multipart ? body : JSON.stringify(body);
  }

  const res = await fetch(url, opts);

  // 204 No Content
  if (res.status === 204) return null;

  let data;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    data = await res.json();
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const error = new APIError(res.status, data);
    window.dispatchEvent(new CustomEvent('aq:api-error', { detail: error }));
    throw error;
  }

  return data;
}

// ─────────────────────────────────────────────
// APIError class
// ─────────────────────────────────────────────
export class APIError extends Error {
  constructor(status, data) {
    super(typeof data === 'string' ? data : (data?.detail || data?.error || data?.message || 'API Error'));
    this.status = status;
    this.data = data;
    this.name = 'APIError';
  }

  get isUnauthorized()  { return this.status === 401; }
  get isForbidden()     { return this.status === 403; }
  get isNotFound()      { return this.status === 404; }
  get isPaymentReq()    { return this.status === 402; }
  get isValidation()    { return this.status === 400 || this.status === 422; }

  // Returns flat list of error messages
  getMessages() {
    if (typeof this.data === 'string') return [this.data];
    if (!this.data || typeof this.data !== 'object') return [this.message];
    const msgs = [];
    function walk(obj, prefix = '') {
      for (const [k, v] of Object.entries(obj)) {
        if (Array.isArray(v)) msgs.push(...v.map(m => prefix ? `${prefix}: ${m}` : m));
        else if (typeof v === 'object' && v !== null) walk(v, k);
        else msgs.push(prefix ? `${prefix}: ${v}` : String(v));
      }
    }
    walk(this.data);
    return msgs.length ? msgs : [this.message];
  }
}

// ─────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────
export const api = {
  get:    (url, params)       => request('GET',    url, { params }),
  post:   (url, body)         => request('POST',   url, { body }),
  put:    (url, body)         => request('PUT',    url, { body }),
  patch:  (url, body)         => request('PATCH',  url, { body }),
  delete: (url)               => request('DELETE', url),
  upload: (url, formData)     => request('POST',   url, { body: formData, multipart: true }),
};

// ─────────────────────────────────────────────
// Auth helpers
// ─────────────────────────────────────────────
export const Auth = {
  async login(username, password) {
    const data = await api.post('/auth/login/', { username, password });
    // Fetch user profile
    TokenStore.set(data.access, data.refresh);
    try {
      const user = await api.get('/users/me/');
      TokenStore.set(data.access, data.refresh, user);
    } catch { /* ignore */ }
    return data;
  },

  async logout() {
    TokenStore.clear();
    redirectToLogin();
  },

  currentUser() { return TokenStore.getUser(); },
  isAuthenticated() { return TokenStore.isAuthenticated(); },
};

function redirectToLogin() {
  const current = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.href = `/login/?next=${current}`;
}

// Auto-redirect on session expiry
window.addEventListener('aq:session-expired', () => redirectToLogin());
