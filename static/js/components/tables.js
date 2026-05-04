/**
 * DataTable Component
 * Tabela com paginação, busca, filtros e ações
 */

export class DataTable {
    constructor(element, config = {}) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.config = {
            endpoint: null,
            columns: [],
            actions: [],
            searchable: true,
            filterable: true,
            sortable: true,
            pagination: true,
            pageSize: 25,
            ...config
        };

        this.data = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.filters = {};

        this.init();
    }

    init() {
        this.render();
        this.bindEvents();
        this.load();
    }

    render() {
        this.element.innerHTML = `
            ${this.config.searchable ? this.renderSearch() : ''}
            ${this.config.filterable ? this.renderFilters() : ''}
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>${this.renderHeader()}</thead>
                    <tbody id="table-body">
                        ${this.renderLoading()}
                    </tbody>
                </table>
            </div>
            ${this.config.pagination ? this.renderPagination() : ''}
            <div id="empty-state" class="empty-state d-none">
                <i class="bi bi-inbox empty-state-icon"></i>
                <h5 class="empty-state-title">Nenhum registro encontrado</h5>
                <p class="empty-state-text">Tente ajustar os filtros ou crie um novo registro.</p>
            </div>
        `;
    }

    renderSearch() {
        return `
            <div class="mb-3">
                <div class="input-group">
                    <span class="input-group-text"><i class="bi bi-search"></i></span>
                    <input type="text" class="form-control" id="table-search"
                           placeholder="Buscar..." aria-label="Buscar">
                </div>
            </div>
        `;
    }

    renderFilters() {
        // Implementar conforme necessidade específica
        return `<div id="table-filters" class="filter-bar"></div>`;
    }

    renderHeader() {
        return `
            <tr>
                ${this.config.columns.map(col => `
                    <th ${col.sortable !== false ? 'class="cursor-pointer" data-sort="' + col.field + '"' : ''}>
                        ${col.label}
                        ${col.sortable !== false ? '<i class="bi bi-arrow-down-up ms-1 small"></i>' : ''}
                    </th>
                `).join('')}
                ${this.config.actions.length ? '<th class="text-end">Ações</th>' : ''}
            </tr>
        `;
    }

    renderRow(item) {
        return `
            <tr data-id="${item.id}">
                ${this.config.columns.map(col => `
                    <td>${this.formatValue(item[col.field], col.format)}</td>
                `).join('')}
                ${this.config.actions.length ? `
                    <td class="text-end">
                        <div class="table-actions">
                            ${this.config.actions.map(action => `
                                <button class="btn btn-sm btn-${action.style || 'light'}"
                                        data-action="${action.name}"
                                        ${action.confirm ? `onclick="return confirm('${action.confirm}')"` : ''}
                                        title="${action.title || ''}">
                                    <i class="bi bi-${action.icon}"></i>
                                </button>
                            `).join('')}
                        </div>
                    </td>
                ` : ''}
            </tr>
        `;
    }

    renderLoading() {
        return `
            <tr>
                <td colspan="${this.config.columns.length + (this.config.actions.length ? 1 : 0)}"
                    class="text-center py-5">
                    <div class="spinner-border text-primary spinner-sm" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                </td>
            </tr>
        `;
    }

    renderPagination() {
        return `
            <div class="pagination-container">
                <span class="pagination-info" id="pagination-info"></span>
                <nav>
                    <ul class="pagination pagination-sm mb-0" id="pagination"></ul>
                </nav>
            </div>
        `;
    }

    formatValue(value, format) {
        if (value === null || value === undefined) return '-';

        switch(format) {
            case 'currency':
                return new Intl.NumberFormat('pt-AO', {
                    style: 'currency', currency: 'AOA'
                }).format(value);
            case 'date':
                return new Date(value).toLocaleDateString('pt-AO');
            case 'datetime':
                return new Date(value).toLocaleString('pt-AO');
            case 'badge':
                return `<span class="badge badge-soft-${value === 'active' ? 'success' : 'secondary'}">${value}</span>`;
            case 'boolean':
                return value ?
                    '<i class="bi bi-check-circle-fill text-success"></i>' :
                    '<i class="bi bi-x-circle-fill text-muted"></i>';
            default:
                return String(value);
        }
    }

    async load() {
        try {
            this.showLoading();

            const params = {
                page: this.currentPage,
                page_size: this.config.pageSize,
                ...this.filters,
            };

            const response = await this.config.apiCall(params);
            this.data = response.results || response;
            this.totalPages = response.total_pages || Math.ceil((response.count || this.data.length) / this.config.pageSize);

            this.renderBody();
            this.updatePagination();
            this.checkEmptyState();

        } catch (error) {
            this.showError(error.message);
            console.error('Error loading data:', error);
        }
    }

    renderBody() {
        const tbody = this.element.querySelector('#table-body');
        if (!this.data.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${this.config.columns.length + (this.config.actions.length ? 1 : 0)}"
                        class="text-center py-4 text-muted">
                        Nenhum dado encontrado
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.data.map(item => this.renderRow(item)).join('');
        this.bindActionEvents();
    }

    updatePagination() {
        if (!this.config.pagination) return;

        const pagination = this.element.querySelector('#pagination');
        const info = this.element.querySelector('#pagination-info');

        const start = (this.currentPage - 1) * this.config.pageSize + 1;
        const end = Math.min(this.currentPage * this.config.pageSize, this.data.length);

        info.textContent = `Mostrando ${start}-${end} de ${this.data.length} registros`;

        let html = '';

        // Previous
        html += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.currentPage - 1}">
                    <i class="bi bi-chevron-left"></i>
                </a>
            </li>
        `;

        // Pages
        const maxPages = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
        let endPage = Math.min(this.totalPages, startPage + maxPages - 1);

        if (endPage - startPage + 1 < maxPages) {
            startPage = Math.max(1, endPage - maxPages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }

        // Next
        html += `
            <li class="page-item ${this.currentPage === this.totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.currentPage + 1}">
                    <i class="bi bi-chevron-right"></i>
                </a>
            </li>
        `;

        pagination.innerHTML = html;
    }

    checkEmptyState() {
        const emptyState = this.element.querySelector('#empty-state');
        const table = this.element.querySelector('table');

        if (!this.data.length && !Object.keys(this.filters).length) {
            emptyState?.classList.remove('d-none');
            table?.classList.add('d-none');
        } else {
            emptyState?.classList.add('d-none');
            table?.classList.remove('d-none');
        }
    }

    showLoading() {
        const tbody = this.element.querySelector('#table-body');
        if (tbody) tbody.innerHTML = this.renderLoading();
    }

    showError(message) {
        const tbody = this.element.querySelector('#table-body');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${this.config.columns.length + (this.config.actions.length ? 1 : 0)}"
                        class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        ${message}
                    </td>
                </tr>
            `;
        }
    }

    bindEvents() {
        // Search
        const searchInput = this.element.querySelector('#table-search');
        if (searchInput) {
            let timeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.filters.search = e.target.value;
                    this.currentPage = 1;
                    this.load();
                }, 300);
            });
        }

        // Sorting
        if (this.config.sortable) {
            this.element.querySelectorAll('[data-sort]').forEach(th => {
                th.addEventListener('click', () => {
                    const field = th.dataset.sort;
                    this.filters.ordering = (this.filters.ordering === field ? '-' + field : field);
                    this.load();
                });
            });
        }

        // Pagination
        this.element.addEventListener('click', (e) => {
            if (e.target.closest('[data-page]')) {
                e.preventDefault();
                const page = parseInt(e.target.closest('[data-page]').dataset.page);
                if (page >= 1 && page <= this.totalPages) {
                    this.currentPage = page;
                    this.load();
                }
            }
        });
    }

    bindActionEvents() {
        this.config.actions.forEach(action => {
            this.element.querySelectorAll(`[data-action="${action.name}"]`).forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const row = e.target.closest('[data-id]');
                    const id = row?.dataset.id;
                    if (id && action.handler) {
                        action.handler(id, this.data.find(item => item.id == id));
                    }
                });
            });
        });
    }

    // Public methods
    refresh() {
        this.load();
    }

    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        this.currentPage = 1;
        this.load();
    }

    clearFilters() {
        this.filters = {};
        const searchInput = this.element.querySelector('#table-search');
        if (searchInput) searchInput.value = '';
        this.load();
    }
}

export default DataTable;
