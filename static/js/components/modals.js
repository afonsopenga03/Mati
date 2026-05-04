/**
 * Modals Component
 * Sistema centralizado de modais dinâmicos
 */

export class ModalManager {
    constructor() {
        this.modals = {};
        this.defaultOptions = {
            backdrop: 'static',
            keyboard: true,
            focus: true,
            size: 'md', // sm, md, lg, xl
            centered: true,
            scrollable: false,
        };
    }

    // Criar modal dinâmico
    create(id, config = {}) {
        const options = { ...this.defaultOptions, ...config };

        const modalHTML = `
            <div class="modal fade" id="${id}" tabindex="-1"
                 aria-labelledby="${id}-label" aria-hidden="true">
                <div class="modal-dialog
                            modal-${options.size}
                            ${options.centered ? 'modal-dialog-centered' : ''}
                            ${options.scrollable ? 'modal-dialog-scrollable' : ''}">
                    <div class="modal-content">
                        ${this.renderHeader(options)}
                        <div class="modal-body" id="${id}-body">
                            ${options.content || ''}
                        </div>
                        ${this.renderFooter(options)}
                    </div>
                </div>
            </div>
        `;

        // Adicionar ao DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Criar instância Bootstrap
        const modalElement = document.getElementById(id);
        const modal = new bootstrap.Modal(modalElement, {
            backdrop: options.backdrop,
            keyboard: options.keyboard,
            focus: options.focus,
        });

        // Guardar referência
        this.modals[id] = {
            instance: modal,
            element: modalElement,
            options: options,
        };

        // Auto-destroy on hidden
        if (options.autoDestroy !== false) {
            modalElement.addEventListener('hidden.bs.modal', () => {
                this.destroy(id);
            });
        }

        return modal;
    }

    renderHeader(options) {
        if (options.hideHeader) return '';

        return `
            <div class="modal-header ${options.headerClass || ''}">
                <h5 class="modal-title" id="${options.id}-label">
                    ${options.title || ''}
                </h5>
                ${options.showClose !== false ?
                    '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>'
                    : ''}
            </div>
        `;
    }

    renderFooter(options) {
        if (options.hideFooter) return '';

        const buttons = options.buttons || [];

        return `
            <div class="modal-footer ${options.footerClass || ''}">
                ${buttons.map(btn => `
                    <button type="button"
                            class="btn btn-${btn.style || 'secondary'}"
                            ${btn.id ? `id="${btn.id}"` : ''}
                            ${btn.disabled ? 'disabled' : ''}
                            data-action="${btn.action || ''}">
                        ${btn.icon ? `<i class="bi bi-${btn.icon} me-1"></i>` : ''}
                        ${btn.text || 'Button'}
                    </button>
                `).join('')}
            </div>
        `;
    }

    // Mostrar modal
    show(id) {
        const modal = this.modals[id];
        if (modal) {
            modal.instance.show();
            return modal;
        }
        throw new Error(`Modal "${id}" not found`);
    }

    // Esconder modal
    hide(id) {
        const modal = this.modals[id];
        if (modal) {
            modal.instance.hide();
        }
    }

    // Atualizar conteúdo do body
    setBodyContent(id, content) {
        const modal = this.modals[id];
        if (modal) {
            const body = modal.element.querySelector('.modal-body');
            if (typeof content === 'string') {
                body.innerHTML = content;
            } else {
                body.innerHTML = '';
                body.appendChild(content);
            }
        }
    }

    // Atualizar título
    setTitle(id, title) {
        const modal = this.modals[id];
        if (modal) {
            const titleEl = modal.element.querySelector('.modal-title');
            if (titleEl) {
                titleEl.textContent = title;
            }
        }
    }

    // Destruir modal
    destroy(id) {
        const modal = this.modals[id];
        if (modal) {
            modal.instance.dispose();
            modal.element.remove();
            delete this.modals[id];
        }
    }

    // Destruir todos
    destroyAll() {
        Object.keys(this.modals).forEach(id => this.destroy(id));
    }
}

// Funções utilitárias pré-configuradas

export function createConfirmModal(options = {}) {
    const {
        id = `confirm-${Date.now()}`,
        title = 'Confirmação',
        message,
        confirmText = 'Confirmar',
        cancelText = 'Cancelar',
        confirmClass = 'btn-primary',
        onConfirm,
        onCancel,
    } = options;

    const modal = new ModalManager();

    modal.create(id, {
        title: title,
        size: 'sm',
        centered: true,
        buttons: [
            { text: cancelText, style: 'secondary', action: 'cancel' },
            { text: confirmText, style: confirmClass, action: 'confirm' },
        ],
    });

    // Event listeners
    const modalEl = document.getElementById(id);

    modalEl.addEventListener('click', (e) => {
        if (e.target.dataset.action === 'confirm') {
            if (onConfirm) onConfirm();
            modal.hide(id);
        } else if (e.target.dataset.action === 'cancel') {
            if (onCancel) onCancel();
            modal.hide(id);
        }
    });

    modal.show(id);
    return id;
}

export function createAlertModal(options = {}) {
    const {
        id = `alert-${Date.now()}`,
        title = 'Aviso',
        message,
        type = 'info', // info, success, warning, danger
        buttonText = 'OK',
        onOk,
    } = options;

    const icons = {
        info: 'info-circle',
        success: 'check-circle',
        warning: 'exclamation-triangle',
        danger: 'x-circle',
    };

    const colors = {
        info: 'primary',
        success: 'success',
        warning: 'warning',
        danger: 'danger',
    };

    const modal = new ModalManager();

    const content = `
        <div class="text-center py-3">
            <i class="bi bi-${icons[type]} text-${colors[type]}"
               style="font-size: 3rem;"></i>
            <p class="mt-3 mb-0">${message}</p>
        </div>
    `;

    modal.create(id, {
        title: title,
        size: 'sm',
        centered: true,
        hideFooter: true,
        content: content,
    });

    // Add OK button to body
    const body = document.querySelector(`#${id} .modal-body`);
    body.insertAdjacentHTML('beforeend', `
        <div class="text-center mt-3">
            <button type="button" class="btn btn-${colors[type]}"
                    data-bs-dismiss="modal">
                ${buttonText}
            </button>
        </div>
    `);

    // Event listener
    const modalEl = document.getElementById(id);
    modalEl.addEventListener('hidden.bs.modal', () => {
        if (onOk) onOk();
    });

    modal.show(id);
    return id;
}

export function createFormModal(options = {}) {
    const {
        id = `form-${Date.now()}`,
        title = 'Formulário',
        fields = [],
        onSubmit,
        submitText = 'Salvar',
        submitClass = 'btn-primary',
    } = options;

    const modal = new ModalManager();

    const formHTML = `
        <form id="${id}-form" novalidate>
            ${fields.map(field => `
                <div class="mb-3">
                    <label class="form-label" for="${id}-${field.name}">
                        ${field.label} ${field.required ? '*' : ''}
                    </label>
                    ${field.type === 'textarea' ? `
                        <textarea class="form-control"
                                  id="${id}-${field.name}"
                                  name="${field.name}"
                                  ${field.required ? 'required' : ''}
                                  rows="${field.rows || 3}">${field.value || ''}</textarea>
                    ` : field.type === 'select' ? `
                        <select class="form-select"
                                id="${id}-${field.name}"
                                name="${field.name}"
                                ${field.required ? 'required' : ''}>
                            <option value="">Selecione...</option>
                            ${(field.options || []).map(opt => `
                                <option value="${opt.value}"
                                        ${opt.value === field.value ? 'selected' : ''}>
                                    ${opt.label}
                                </option>
                            `).join('')}
                        </select>
                    ` : `
                        <input type="${field.type || 'text'}"
                               class="form-control"
                               id="${id}-${field.name}"
                               name="${field.name}"
                               value="${field.value || ''}"
                               ${field.required ? 'required' : ''}
                               ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}>
                    `}
                    ${field.helpText ? `<small class="form-text text-muted">${field.helpText}</small>` : ''}
                </div>
            `).join('')}
        </form>
    `;

    modal.create(id, {
        title: title,
        size: options.size || 'md',
        content: formHTML,
        buttons: [
            { text: 'Cancelar', style: 'secondary', action: 'cancel' },
            { text: submitText, style: submitClass, action: 'submit' },
        ],
    });

    // Handle submit
    const modalEl = document.getElementById(id);
    modalEl.addEventListener('click', async (e) => {
        if (e.target.dataset.action === 'submit') {
            const form = document.getElementById(`${id}-form`);
            if (form.checkValidity()) {
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());

                try {
                    if (onSubmit) {
                        await onSubmit(data);
                    }
                    modal.hide(id);
                } catch (error) {
                    alert('Erro: ' + error.message);
                }
            } else {
                form.classList.add('was-validated');
            }
        } else if (e.target.dataset.action === 'cancel') {
            modal.hide(id);
        }
    });

    modal.show(id);
    return id;
}

// Export default
export default {
    ModalManager,
    createConfirmModal,
    createAlertModal,
    createFormModal,
};
