/**
 * Base JavaScript - Water Management System
 * Inicialização global e utilitários
 */

// Configurações globais
window.Mati = {
    config: {
        apiBase: '/api/v1',
        csrfToken: document.querySelector('[name=csrf-token]')?.content ||
                   document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1],
        locale: document.documentElement.lang || 'pt-AO',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    },

    // Utilitários
    utils: {
        // Format currency
        formatCurrency: (value, currency = 'AOA') => {
            return new Intl.NumberFormat('pt-AO', {
                style: 'currency',
                currency: currency
            }).format(value);
        },

        // Format date
        formatDate: (date, options = {}) => {
            const defaultOptions = {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                ...options
            };
            return new Date(date).toLocaleDateString('pt-AO', defaultOptions);
        },

        // Format datetime
        formatDateTime: (date) => {
            return new Date(date).toLocaleString('pt-AO', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },

        // Debounce function
        debounce: (func, wait) => {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        // Generate UUID
        uuid: () => {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        },

        // Parse query string
        parseQuery: (queryString) => {
            const params = {};
            new URLSearchParams(queryString).forEach((value, key) => {
                params[key] = value;
            });
            return params;
        },

        // Build query string
        buildQuery: (params) => {
            return new URLSearchParams(params).toString();
        }
    },

    // State management simples
    state: {
        store: {},
        set(key, value) {
            this.store[key] = value;
            // Dispatch event para reatividade
            window.dispatchEvent(new CustomEvent(`state:${key}`, { detail: value }));
        },
        get(key, defaultValue = null) {
            return this.store[key] ?? defaultValue;
        },
        subscribe(key, callback) {
            const handler = (e) => callback(e.detail);
            window.addEventListener(`state:${key}`, handler);
            return () => window.removeEventListener(`state:${key}`, handler);
        }
    }
};

// Inicialização quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el, { trigger: 'hover' }));

    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(el => new bootstrap.Popover(el));

    // Sidebar toggle para mobile
    const sidebarToggle = document.querySelector('[data-bs-toggle="sidebar"]');
    const sidebar = document.querySelector('#sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });

        // Fechar sidebar ao clicar fora em mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 768 &&
                !sidebar.contains(e.target) &&
                !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // Auto-hide messages after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirm links with data-confirm attribute
    document.querySelectorAll('a[data-confirm]').forEach(link => {
        link.addEventListener('click', (e) => {
            if (!confirm(link.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Form submission with loading state
    document.querySelectorAll('form[data-loading]').forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-1"></span>
                    ${submitBtn.dataset.loadingText || 'Processando...'}
                `;
            }
        });
    });

    // Console welcome message
    console.log('%c🚀 Mati Water Management System', 'font-size: 14px; font-weight: bold; color: #0d6efd;');
    console.log('%cVersão: 1.0.0 | Ambiente: ' + (window.location.hostname === 'localhost' ? 'Development' : 'Production'), 'font-size: 11px; color: #6c757d;');
});

// Global error handler
window.addEventListener('error', (e) => {
    // Log errors para monitoramento (em produção, enviar para serviço de logging)
    if (window.Mati.config.environment !== 'development') {
        console.error('Global error:', {
            message: e.message,
            source: e.filename,
            lineno: e.lineno,
            colno: e.colno,
            stack: e.error?.stack
        });
    }
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    // Em produção: enviar para serviço de monitoramento
});

// Export para módulos
export default window.Mati;
