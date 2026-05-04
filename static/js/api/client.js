/**
 * ============================================================================
 * MATI - Water Management System
 * API Client Module - Production Ready
 * ============================================================================
 *
 * Configuração centralizada para comunicação com Django REST Framework + SimpleJWT
 *
 * Features:
 * • JWT Bearer Token Authentication
 * • CSRF Token support para Session Auth fallback
 * • Paginação compatível com StandardResultsPagination
 * • Timeout com AbortController
 * • Upload de arquivos com FormData
 * • Tratamento de erros padronizado
 * • Request/Response interceptors para extensibilidade
 * • Download de blobs (PDFs, exports)
 *
 * @author Mati Team
 * @version 2.0.0
 * @requires Bootstrap 5 (para notificações opcionais)
 */

// ============================================================================
// CONFIGURAÇÃO GLOBAL
// ============================================================================

const API_CONFIG = {
    /** Base URL da API - relativo para mesmo domínio ou absoluto para CORS */
    baseURL: '/api',

    /** Timeout padrão para requisições (ms) */
    timeout: 30000,

    /** Headers padrão enviados em todas as requisições */
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },

    /** Chave do localStorage para armazenar tokens */
    storageKeys: {
        accessToken: 'mati_access_token',
        refreshToken: 'mati_refresh_token',
        userInfo: 'mati_user_info',
    },

    /** Endpoints de autenticação */
    auth: {
        login: '/auth/login/',
        refresh: '/auth/token/refresh/',
        logout: '/auth/logout/',
    },
};

// ============================================================================
// CLASSES DE ERRO PERSONALIZADAS
// ============================================================================

/**
 * Erro base para falhas na API
 */
export class APIError extends Error {
    constructor(message, status, data = null, errors = null) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
        this.errors = errors; // Validação de formulário DRF
        this.timestamp = new Date().toISOString();
    }

    /** Verifica se é erro de validação de formulário */
    isValidationError() {
        return this.status === 400 && this.errors;
    }

    /** Verifica se é erro de autenticação */
    isAuthError() {
        return [401, 403].includes(this.status);
    }

    /** Formata erros de validação para exibição */
    getFormattedErrors() {
        if (!this.errors || typeof this.errors !== 'object') return [];

        return Object.entries(this.errors).flatMap(([field, messages]) => {
            if (Array.isArray(messages)) {
                return messages.map(msg => ({ field, message: msg }));
            }
            return [{ field, message: messages }];
        });
    }
}

/**
 * Erro para timeout de requisição
 */
export class TimeoutError extends APIError {
    constructor(endpoint) {
        super(`Timeout na requisição para ${endpoint}`, 408);
        this.name = 'TimeoutError';
    }
}

/**
 * Erro para falha de conexão/network
 */
export class NetworkError extends APIError {
    constructor(message = 'Falha de conexão com o servidor') {
        super(message, 0);
        this.name = 'NetworkError';
    }
}

// ============================================================================
// API CLIENT - CLASSE PRINCIPAL
// ============================================================================

export class APIClient {
    constructor(config = {}) {
        this.config = { ...API_CONFIG, ...config };
        this.interceptors = {
            request: [],
            response: [],
            error: [],
        };
    }

    // =========================================================================
    // GERENCIAMENTO DE TOKENS
    // =========================================================================

    /**
     * Obtém token de acesso do localStorage
     * @returns {string|null}
     */
    getAccessToken() {
        return localStorage.getItem(this.config.storageKeys.accessToken);
    }

    /**
     * Obtém token de refresh do localStorage
     * @returns {string|null}
     */
    getRefreshToken() {
        return localStorage.getItem(this.config.storageKeys.refreshToken);
    }

    /**
     * Define tokens no localStorage
     * @param {string} access - Access token JWT
     * @param {string} [refresh] - Refresh token JWT (opcional)
     */
    setTokens(access, refresh = null) {
        localStorage.setItem(this.config.storageKeys.accessToken, access);
        if (refresh) {
            localStorage.setItem(this.config.storageKeys.refreshToken, refresh);
        }
    }

    /**
     * Remove todos os tokens (logout)
     */
    clearTokens() {
        localStorage.removeItem(this.config.storageKeys.accessToken);
        localStorage.removeItem(this.config.storageKeys.refreshToken);
        localStorage.removeItem(this.config.storageKeys.userInfo);
    }

    /**
     * Obtém CSRF token do cookie do Django
     * @returns {string|null}
     */
    getCSRFToken() {
        return document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
    }

    /**
     * Verifica se usuário está autenticado
     * @returns {boolean}
     */
    isAuthenticated() {
        return !!this.getAccessToken();
    }

    // =========================================================================
    // CONFIGURAÇÃO DE HEADERS
    // =========================================================================

    /**
     * Monta headers padrão para requisição
     * @param {Object} customHeaders - Headers adicionais
     * @param {boolean} includeAuth - Incluir token de autenticação
     * @param {boolean} isFormData - Se é upload de arquivo
     * @returns {Headers}
     */
    buildHeaders(customHeaders = {}, includeAuth = true, isFormData = false) {
        const headers = new Headers(this.config.headers);

        // Remove Content-Type para FormData (browser define boundary automaticamente)
        if (isFormData) {
            headers.delete('Content-Type');
        }

        // Adiciona headers customizados
        Object.entries(customHeaders).forEach(([key, value]) => {
            if (value !== undefined) {
                headers.set(key, value);
            }
        });

        // Adiciona token JWT se disponível e solicitado
        if (includeAuth) {
            const token = this.getAccessToken();
            if (token) {
                headers.set('Authorization', `Bearer ${token}`);
            }
        }

        // Adiciona CSRF token para segurança Django (session auth fallback)
        const csrfToken = this.getCSRFToken();
        if (csrfToken) {
            headers.set('X-CSRFToken', csrfToken);
        }

        return headers;
    }

    // =========================================================================
    // INTERCEPTORS
    // =========================================================================

    /**
     * Registra interceptor de request
     * @param {Function} handler - (config) => config | Promise<config>
     */
    useRequestInterceptor(handler) {
        this.interceptors.request.push(handler);
    }

    /**
     * Registra interceptor de response
     * @param {Function} handler - (response) => response | Promise<response>
     */
    useResponseInterceptor(handler) {
        this.interceptors.response.push(handler);
    }

    /**
     * Registra interceptor de erro
     * @param {Function} handler - (error) => handled | Promise<handled>
     */
    useErrorInterceptor(handler) {
        this.interceptors.error.push(handler);
    }

    /**
     * Executa interceptors de request em cadeia
     * @param {Object} config
     * @returns {Promise<Object>}
     */
    async applyRequestInterceptors(config) {
        let result = config;
        for (const handler of this.interceptors.request) {
            result = await Promise.resolve(handler(result));
        }
        return result;
    }

    /**
     * Executa interceptors de response em cadeia
     * @param {Response} response
     * @returns {Promise<Response>}
     */
    async applyResponseInterceptors(response) {
        let result = response;
        for (const handler of this.interceptors.response) {
            result = await Promise.resolve(handler(result));
        }
        return result;
    }

    // =========================================================================
    // MÉTODO PRINCIPAL DE REQUEST
    // =========================================================================

    /**
     * Executa requisição HTTP genérica
     * @param {string} endpoint - Endpoint relativo (ex: '/companies/')
     * @param {Object} options - Opções do fetch
     * @param {Object} meta - Metadados para logging/debug
     * @returns {Promise<any>} Dados da resposta ou null para 204
     */
    async request(endpoint, options = {}, meta = {}) {
        const {
            timeout = this.config.timeout,
            includeAuth = true,
            isFormData = false,
            responseType = 'json', // 'json' | 'blob' | 'text'
            skipInterceptors = false,
        } = options;

        const url = `${this.config.baseURL}${endpoint}`;
        const requestId = meta.requestId || crypto.randomUUID?.() || Date.now();

        // Configuração base da requisição
        let config = {
            ...options,
            headers: this.buildHeaders(options.headers, includeAuth, isFormData),
        };

        // Aplica interceptors de request
        if (!skipInterceptors) {
            config = await this.applyRequestInterceptors({ ...config, endpoint, requestId });
        }

        // Setup de timeout com AbortController
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            // Logging em desenvolvimento
            if (process.env.NODE_ENV !== 'production') {
                console.group(`🔗 [API] ${config.method?.toUpperCase() || 'GET'} ${endpoint}`);
                console.log('Request ID:', requestId);
                console.log('Headers:', Object.fromEntries(config.headers));
                if (config.body && !isFormData) {
                    console.log('Body:', JSON.parse(config.body));
                }
                console.groupEnd();
            }

            // Executa fetch
            const response = await fetch(url, {
                ...config,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            // Aplica interceptors de response
            if (!skipInterceptors) {
                await this.applyResponseInterceptors(response);
            }

            // Tratamento de respostas de erro HTTP
            if (!response.ok) {
                let errorData = null;
                let errorText = null;

                try {
                    // Tenta parsear JSON de erro
                    errorData = await response.clone().json();
                } catch {
                    // Fallback para texto
                    errorText = await response.clone().text();
                }

                const errorMessage = errorData?.detail
                    || errorData?.message
                    || errorData?.non_field_errors?.[0]
                    || errorText
                    || response.statusText
                    || 'Erro desconhecido na API';

                throw new APIError(
                    errorMessage,
                    response.status,
                    errorData,
                    errorData && typeof errorData === 'object' && !Array.isArray(errorData)
                        ? errorData
                        : null
                );
            }

            // Respostas 204 No Content
            if (response.status === 204) {
                return null;
            }

            // Parse da resposta conforme tipo solicitado
            switch (responseType) {
                case 'blob':
                    return await response.blob();
                case 'text':
                    return await response.text();
                case 'json':
                default:
                    return await response.json();
            }

        } catch (error) {
            clearTimeout(timeoutId);

            // Tratamento de erros específicos
            if (error.name === 'AbortError') {
                throw new TimeoutError(endpoint);
            }

            if (error instanceof APIError) {
                // Aplica interceptors de erro para APIError
                if (!skipInterceptors && this.interceptors.error.length) {
                    for (const handler of this.interceptors.error) {
                        try {
                            return await Promise.resolve(handler(error));
                        } catch {
                            // Continua para próximo interceptor
                        }
                    }
                }
                throw error;
            }

            if (error instanceof TypeError && error.message.includes('fetch')) {
                throw new NetworkError();
            }

            // Erro não esperado - repassa com wrapper
            throw new APIError(
                error.message || 'Erro interno no cliente API',
                error.status || 500,
                null,
                { __unexpected__: true, original: error }
            );

        } finally {
            // Cleanup sempre executado
            clearTimeout(timeoutId);
        }
    }

    // =========================================================================
    // MÉTODOS HTTP CONVENIENTES
    // =========================================================================

    /**
     * GET request com suporte a query params
     * @param {string} endpoint
     * @param {Object} params - Query parameters
     * @param {Object} options - Opções adicionais
     */
    get(endpoint, params = {}, options = {}) {
        const queryString = params ? new URLSearchParams(params).toString() : '';
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET', ...options });
    }

    /**
     * POST request com body JSON
     * @param {string} endpoint
     * @param {Object} data - Dados a enviar
     * @param {Object} options - Opções adicionais
     */
    post(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
            ...options,
        });
    }

    /**
     * PUT request (substituição completa)
     * @param {string} endpoint
     * @param {Object} data
     * @param {Object} options
     */
    put(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
            ...options,
        });
    }

    /**
     * PATCH request (atualização parcial)
     * @param {string} endpoint
     * @param {Object} data
     * @param {Object} options
     */
    patch(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data),
            ...options,
        });
    }

    /**
     * DELETE request
     * @param {string} endpoint
     * @param {Object} options
     */
    delete(endpoint, options = {}) {
        return this.request(endpoint, {
            method: 'DELETE',
            ...options,
        });
    }

    // =========================================================================
    // UPLOAD DE ARQUIVOS
    // =========================================================================

    /**
     * Upload de arquivo com FormData
     * @param {string} endpoint
     * @param {File|Blob} file - Arquivo a enviar
     * @param {Object} extraFields - Campos adicionais do FormData
     * @param {Function} onProgress - Callback de progresso (bytes enviados, total)
     */
    async upload(endpoint, file, extraFields = {}, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file, file.name);

        // Adiciona campos extras
        Object.entries(extraFields).forEach(([key, value]) => {
            formData.append(key, value);
        });

        // Nota: Fetch API não suporta onprogress nativamente
        // Para progresso real, considere usar XMLHttpRequest ou axios
        return this.request(endpoint, {
            method: 'POST',
            body: formData,
            isFormData: true,
        });
    }

    /**
     * Upload múltiplo de arquivos
     * @param {string} endpoint
     * @param {File[]} files
     * @param {Object} extraFields
     */
    async uploadMultiple(endpoint, files, extraFields = {}) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file, file.name));

        Object.entries(extraFields).forEach(([key, value]) => {
            formData.append(key, value);
        });

        return this.request(endpoint, {
            method: 'POST',
            body: formData,
            isFormData: true,
        });
    }

    // =========================================================================
    // DOWNLOAD DE ARQUIVOS
    // =========================================================================

    /**
     * Download de arquivo como blob (PDF, CSV, Excel)
     * @param {string} endpoint
     * @param {Object} params - Query params
     * @param {string} filename - Nome sugerido para download
     */
    async download(endpoint, params = {}, filename = 'download') {
        const blob = await this.get(endpoint, params, { responseType: 'blob' });

        // Cria link temporário para download
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();

        // Cleanup
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        return blob;
    }

    // =========================================================================
    // AUTENTICAÇÃO - MÉTODOS CONVENIENTES
    // =========================================================================

    /**
     * Login com credenciais
     * @param {string} username
     * @param {string} password
     * @returns {Promise<{access: string, refresh: string, user: Object}>}
     */
    async login(username, password) {
        const response = await this.post(this.config.auth.login, { username, password });

        // Armazena tokens
        this.setTokens(response.access, response.refresh);

        // Armazena info do usuário se disponível
        if (response.user) {
            localStorage.setItem(this.config.storageKeys.userInfo, JSON.stringify(response.user));
        }

        return response;
    }

    /**
     * Refresh do token de acesso
     * @returns {Promise<string>} Novo access token
     */
    async refreshAccessToken() {
        const refresh = this.getRefreshToken();
        if (!refresh) {
            throw new APIError('Refresh token não encontrado', 401);
        }

        const response = await this.post(
            this.config.auth.refresh,
            { refresh },
            { includeAuth: false } // Refresh endpoint não requer auth header
        );

        // Atualiza apenas o access token
        localStorage.setItem(this.config.storageKeys.accessToken, response.access);

        return response.access;
    }

    /**
     * Logout - limpa tokens e notifica backend se necessário
     */
    async logout() {
        // Tenta notificar backend (opcional, falha silenciosa se offline)
        try {
            await this.post(this.config.auth.logout, {}, { timeout: 5000 });
        } catch {
            // Ignora erro de rede no logout
        }

        // Limpa tokens locais
        this.clearTokens();
    }

    /**
     * Obtém info do usuário do localStorage
     * @returns {Object|null}
     */
    getUserInfo() {
        const raw = localStorage.getItem(this.config.storageKeys.userInfo);
        return raw ? JSON.parse(raw) : null;
    }

    // =========================================================================
    // UTILITÁRIOS PARA PAGINAÇÃO DRF
    // =========================================================================

    /**
     * Extrai dados de lista paginada do DRF
     * @param {Object} response - Resposta da API
     * @returns {{items: Array, pagination: Object}}
     */
    parsePaginatedResponse(response) {
        // Detecta se é resposta paginada do DRF
        if (response && Array.isArray(response.results)) {
            return {
                items: response.results,
                pagination: {
                    count: response.count,
                    next: response.next,
                    previous: response.previous,
                    currentPage: this.extractPageFromUrl(response.next || response.previous),
                    totalPages: response.total_pages || null, // Se usar custom pagination
                    hasNext: !!response.next,
                    hasPrevious: !!response.previous,
                }
            };
        }

        // Resposta não paginada (array direto ou objeto)
        return {
            items: Array.isArray(response) ? response : [response].filter(Boolean),
            pagination: null,
        };
    }

    /**
     * Extrai número da página de uma URL de paginação DRF
     * @param {string|null} url
     * @returns {number|null}
     */
    extractPageFromUrl(url) {
        if (!url) return null;
        try {
            const params = new URL(url).searchParams;
            const page = params.get('page');
            return page ? parseInt(page, 10) : null;
        } catch {
            return null;
        }
    }

    /**
     * Constrói parâmetros de paginação para próxima/anterior página
     * @param {Object} pagination
     * @param {'next'|'previous'} direction
     * @returns {Object|null}
     */
    getPaginationParams(pagination, direction) {
        if (!pagination) return null;

        const url = pagination[direction];
        if (!url) return null;

        try {
            const params = new URL(url).searchParams;
            return Object.fromEntries(params.entries());
        } catch {
            return null;
        }
    }
}

// ============================================================================
// EXPORTAÇÕES E SINGLETON
// ============================================================================

/**
 * Instância singleton para uso global
 * @type {APIClient}
 */
export const api = new APIClient();

/**
 * Export default para compatibilidade
 */
export default api;

// ============================================================================
// INTERCEPTORS PRÉ-CONFIGURADOS (OPCIONAL)
// ============================================================================

/**
 * Interceptor para logging de requisições em desenvolvimento
 */
if (process.env.NODE_ENV !== 'production') {
    api.useRequestInterceptor(config => {
        console.log(`[API Request] ${config.method?.toUpperCase()} ${config.endpoint}`);
        return config;
    });

    api.useResponseInterceptor(async response => {
        console.log(`[API Response] ${response.status} ${response.url}`);
        return response;
    });
}

/**
 * Interceptor para auto-refresh de token em 401
 *
 * ⚠️ Atenção: Pode causar loop se refresh também falhar
 * Use com cuidado e considere implementar fila de retry
 */
let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(callback) {
    refreshSubscribers.push(callback);
}

function onTokenRefreshed(newToken) {
    refreshSubscribers.forEach(cb => cb(newToken));
    refreshSubscribers = [];
}

api.useErrorInterceptor(async error => {
    // Apenas trata 401 de autenticação (não de permissão 403)
    if (error.status === 401 && !error.config?.skipTokenRefresh) {

        // Se já está refreshando, aguarda e retry
        if (isRefreshing) {
            return new Promise(resolve => {
                subscribeTokenRefresh(async newToken => {
                    // Retry da requisição original com novo token
                    error.config.headers.set('Authorization', `Bearer ${newToken}`);
                    const response = await fetch(error.config.url, error.config);
                    resolve(response.json());
                });
            });
        }

        // Inicia processo de refresh
        isRefreshing = true;

        try {
            const newToken = await api.refreshAccessToken();
            onTokenRefreshed(newToken);

            // Retry da requisição original
            error.config.headers.set('Authorization', `Bearer ${newToken}`);
            const response = await fetch(error.config.url, error.config);
            return response.json();

        } catch (refreshError) {
            // Refresh falhou → força logout
            api.clearTokens();
            window.location.href = '/login/?session=expired';
            throw refreshError;

        } finally {
            isRefreshing = false;
        }
    }

    // Repassa outros erros
    throw error;
});

// ============================================================================
// UTILITÁRIOS GLOBAIS (para uso em templates Django)
// ============================================================================

/**
 * Inicializa o cliente API com dados do template Django
 *
 * Uso em template:
 * <script>
 *   window.MatiAPI.init({
 *     csrfToken: '{{ csrf_token }}',
 *     initialUser: {{ user_json|safe }},
 *   });
 * </script>
 */
export function initClient(options = {}) {
    // Configura CSRF se fornecido via template
    if (options.csrfToken) {
        document.cookie = `csrftoken=${options.csrfToken}; path=/; SameSite=Lax`;
    }

    // Configura usuário inicial se fornecido
    if (options.initialUser) {
        localStorage.setItem(api.config.storageKeys.userInfo, JSON.stringify(options.initialUser));
    }

    // Configura base URL dinâmica se necessário
    if (options.baseURL) {
        api.config.baseURL = options.baseURL;
    }

    return api;
}

// Expõe globalmente para templates Django (opcional)
if (typeof window !== 'undefined') {
    window.MatiAPI = {
        api,
        init: initClient,
        APIError,
        TimeoutError,
        NetworkError,
    };
}
