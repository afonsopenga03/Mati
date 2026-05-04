/**
 * API Client - Water Management System
 * Configuração centralizada para chamadas à API DRF
 */

const API_CONFIG = {
    baseURL: '/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
};

class APIError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }
}

class APIClient {
    constructor(config = {}) {
        this.config = { ...API_CONFIG, ...config };
        this.token = this.getAuthToken();
    }

    getAuthToken() {
        return localStorage.getItem('auth_token') ||
               document.querySelector('meta[name="csrf-token"]')?.content;
    }

    setAuthToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    }

    clearAuthToken() {
        this.token = null;
        localStorage.removeItem('auth_token');
    }

    async request(endpoint, options = {}) {
        const url = `${this.config.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.config.headers,
                ...(this.token && { 'Authorization': `Token ${this.token}` }),
                ...options.headers,
            },
        };

        // Add CSRF token for Django
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];

        if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken;
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

            const response = await fetch(url, {
                ...config,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    errorData = { detail: response.statusText };
                }
                throw new APIError(
                    errorData.detail || errorData.message || 'Erro na requisição',
                    response.status,
                    errorData
                );
            }

            // Handle no-content responses
            if (response.status === 204) {
                return null;
            }

            return await response.json();

        } catch (error) {
            if (error.name === 'AbortError') {
                throw new APIError('Tempo de espera excedido', 408, null);
            }
            if (error instanceof APIError) {
                throw error;
            }
            throw new APIError('Erro de conexão com o servidor', 0, null);
        }
    }

    // HTTP Methods
    get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return this.request(`${endpoint}${queryString ? '?' + queryString : ''}`, {
            method: 'GET',
        });
    }

    post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    patch(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE',
        });
    }

    // Upload file
    upload(endpoint, file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);

        return this.request(endpoint, {
            method: 'POST',
            body: formData,
            headers: {
                // Remove Content-Type for multipart/form-data
                'Content-Type': undefined,
            },
        });
    }
}

// Export singleton instance
export const api = new APIClient();
export default APIClient;
