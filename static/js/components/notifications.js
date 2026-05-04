/**
 * Notifications Module
 * Sistema de notificações toast com Bootstrap 5
 */

export const ToastType = {
    SUCCESS: 'success',
    ERROR: 'danger',
    WARNING: 'warning',
    INFO: 'info'
};

const ToastIcons = {
    [ToastType.SUCCESS]: 'bi-check-circle-fill',
    [ToastType.ERROR]: 'bi-exclamation-triangle-fill',
    [ToastType.WARNING]: 'bi-exclamation-circle-fill',
    [ToastType.INFO]: 'bi-info-circle-fill'
};

// Container global para toasts
let toastContainer = null;

function getContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1080';
        toastContainer.style.marginTop = '56px'; // Navbar height
        document.body.appendChild(toastContainer);
    }
    return toastContainer;
}

// Função principal para mostrar toast
export function showToast(message, type = ToastType.INFO, options = {}) {
    const {
        title = null,
        duration = 5000,
        showClose = true,
        onClick = null,
        id = null
    } = options;

    const container = getContainer();
    const toastId = id || `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center border-0 shadow"
             role="alert" aria-live="assertive" aria-atomic="true"
             data-bs-delay="${duration}">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center ${type === ToastType.ERROR ? 'text-danger' : ''}">
                    <i class="bi ${ToastIcons[type]} me-2 fs-5"></i>
                    <div class="flex-grow-1">
                        ${title ? `<strong class="d-block">${title}</strong>` : ''}
                        <span>${message}</span>
                    </div>
                </div>
                ${showClose ? `<button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>` : ''}
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        delay: duration,
        autohide: duration > 0
    });

    // Click handler
    if (onClick) {
        toastElement.addEventListener('click', (e) => {
            if (!e.target.closest('[data-bs-dismiss]')) {
                onClick();
                toast.hide();
            }
        });
        toastElement.style.cursor = 'pointer';
    }

    // Auto-remove after hide
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });

    toast.show();

    return {
        hide: () => toast.hide(),
        element: toastElement
    };
}

// Funções convenientes por tipo
export const notify = {
    success: (message, options) => showToast(message, ToastType.SUCCESS, options),
    error: (message, options) => showToast(message, ToastType.ERROR, options),
    warning: (message, options) => showToast(message, ToastType.WARNING, options),
    info: (message, options) => showToast(message, ToastType.INFO, options),
};

// Mostrar múltiplas notificações (ex: erros de formulário)
export function showValidationErrors(errors) {
    if (Array.isArray(errors)) {
        errors.forEach(err => notify.error(err));
    } else if (typeof errors === 'object') {
        Object.entries(errors).forEach(([field, messages]) => {
            if (Array.isArray(messages)) {
                messages.forEach(msg => notify.error(`${field}: ${msg}`));
            } else {
                notify.error(`${field}: ${messages}`);
            }
        });
    }
}

// Confirmar ação com modal customizado
export function confirmAction(title, message, options = {}) {
    return new Promise((resolve) => {
        const {
            confirmText = 'Confirmar',
            cancelText = 'Cancelar',
            confirmClass = 'btn-danger'
        } = options;

        const modalId = `confirm-modal-${Date.now()}`;
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body pt-0">
                            <p class="mb-0">${message}</p>
                        </div>
                        <div class="modal-footer border-0 pt-0">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                ${cancelText}
                            </button>
                            <button type="button" class="btn ${confirmClass}" id="${modalId}-confirm">
                                ${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);

        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();

        document.getElementById(`${modalId}-confirm`).addEventListener('click', () => {
            resolve(true);
            modal.hide();
        });

        document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
            document.getElementById(modalId)?.remove();
            resolve(false);
        });
    });
}

// Mostrar loading em botão
export function withLoading(button, promise) {
    const originalContent = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Processando...';

    return promise
        .then(result => {
            button.disabled = false;
            button.innerHTML = originalContent;
            return result;
        })
        .catch(error => {
            button.disabled = false;
            button.innerHTML = originalContent;
            throw error;
        });
}

export default {
    showToast,
    notify,
    showValidationErrors,
    confirmAction,
    withLoading,
    ToastType
};
