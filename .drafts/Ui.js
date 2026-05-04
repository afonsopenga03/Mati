/**
 * AquaGest UI Utilities
 * Toast, Modal, Loader, DynamicTable, DynamicForm
 */

// ─────────────────────────────────────────────
// Toast / Alerts
// ─────────────────────────────────────────────
export const Toast = {
  _container: null,

  _getContainer() {
    if (!this._container) {
      this._container = document.createElement('div');
      this._container.id = 'aq-toast-container';
      this._container.style.cssText = `
        position:fixed; top:20px; right:20px; z-index:9999;
        display:flex; flex-direction:column; gap:10px; max-width:360px;
      `;
      document.body.appendChild(this._container);
    }
    return this._container;
  },

  show(message, type = 'info', duration = 4000) {
    const colors = {
      success: { bg: 'rgba(34,211,165,0.1)',  border: '#22d3a5', icon: '✓', color: '#22d3a5' },
      error:   { bg: 'rgba(244,63,94,0.1)',   border: '#f43f5e', icon: '✕', color: '#f43f5e' },
      warning: { bg: 'rgba(245,158,11,0.1)',  border: '#f59e0b', icon: '⚠', color: '#f59e0b' },
      info:    { bg: 'rgba(0,212,255,0.1)',   border: '#00d4ff', icon: 'ℹ', color: '#00d4ff' },
    };
    const c = colors[type] || colors.info;

    const el = document.createElement('div');
    el.style.cssText = `
      background:${c.bg}; border:1px solid ${c.border}; border-radius:10px;
      padding:14px 18px; color:#e2e8f4; font-family:'DM Sans',sans-serif;
      font-size:.875rem; display:flex; align-items:flex-start; gap:12px;
      animation:toastIn .3s ease both; backdrop-filter:blur(10px);
      box-shadow:0 8px 32px rgba(0,0,0,.4);
    `;
    el.innerHTML = `
      <span style="color:${c.color};font-size:1rem;flex-shrink:0;margin-top:1px">${c.icon}</span>
      <span style="flex:1;line-height:1.5">${message}</span>
      <button onclick="this.closest('[style]').remove()" style="background:none;border:none;color:#5a7295;cursor:pointer;font-size:1rem;padding:0;flex-shrink:0">×</button>
    `;

    const style = document.getElementById('aq-toast-style');
    if (!style) {
      const s = document.createElement('style');
      s.id = 'aq-toast-style';
      s.textContent = `
        @keyframes toastIn { from { opacity:0; transform:translateX(20px); } to { opacity:1; transform:none; } }
        @keyframes toastOut { from { opacity:1; transform:none; } to { opacity:0; transform:translateX(20px); } }
      `;
      document.head.appendChild(s);
    }

    this._getContainer().appendChild(el);

    if (duration > 0) {
      setTimeout(() => {
        el.style.animation = 'toastOut .3s ease both';
        setTimeout(() => el.remove(), 300);
      }, duration);
    }

    return el;
  },

  success: (msg, d) => Toast.show(msg, 'success', d),
  error:   (msg, d) => Toast.show(msg, 'error', d),
  warning: (msg, d) => Toast.show(msg, 'warning', d),
  info:    (msg, d) => Toast.show(msg, 'info', d),

  apiError(err) {
    const msgs = err.getMessages?.() || [err.message];
    msgs.forEach(m => this.error(m));
  },
};

// ─────────────────────────────────────────────
// Loader
// ─────────────────────────────────────────────
export const Loader = {
  _el: null,

  show(text = 'Carregando...') {
    if (this._el) return;
    this._el = document.createElement('div');
    this._el.style.cssText = `
      position:fixed; inset:0; background:rgba(7,13,26,.8); backdrop-filter:blur(4px);
      display:flex; flex-direction:column; align-items:center; justify-content:center;
      z-index:9998; gap:16px;
    `;
    this._el.innerHTML = `
      <div style="
        width:44px; height:44px; border:3px solid rgba(0,212,255,0.15);
        border-top-color:#00d4ff; border-radius:50%;
        animation:spin .8s linear infinite;
      "></div>
      <span style="color:#e2e8f4;font-family:'DM Sans',sans-serif;font-size:.875rem;color:#6b7fa3">${text}</span>
    `;
    if (!document.getElementById('aq-spin')) {
      const s = document.createElement('style');
      s.id = 'aq-spin';
      s.textContent = '@keyframes spin { to { transform:rotate(360deg); } }';
      document.head.appendChild(s);
    }
    document.body.appendChild(this._el);
  },

  hide() {
    this._el?.remove();
    this._el = null;
  },

  // Wrap async call with loader
  async wrap(fn, text) {
    this.show(text);
    try { return await fn(); }
    finally { this.hide(); }
  },
};

// ─────────────────────────────────────────────
// Button loading state
// ─────────────────────────────────────────────
export function btnLoading(btn, loading, originalText) {
  if (loading) {
    btn.disabled = true;
    btn._originalText = btn.innerHTML;
    btn.innerHTML = `<span style="display:inline-flex;align-items:center;gap:8px">
      <span style="width:14px;height:14px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite;display:inline-block"></span>
      Aguarde...
    </span>`;
  } else {
    btn.disabled = false;
    btn.innerHTML = btn._originalText || originalText || btn.innerHTML;
  }
}

// ─────────────────────────────────────────────
// Modal
// ─────────────────────────────────────────────
export class Modal {
  constructor({ id, title, body, size = 'md', footer = null, onClose = null }) {
    this.id = id || `modal-${Date.now()}`;
    this.onClose = onClose;
    this._build(title, body, size, footer);
  }

  _build(title, body, size, footer) {
    const widths = { sm: '480px', md: '600px', lg: '800px', xl: '1000px' };
    const existing = document.getElementById(this.id);
    if (existing) existing.remove();

    this.overlay = document.createElement('div');
    this.overlay.id = this.id;
    this.overlay.style.cssText = `
      position:fixed; inset:0; background:rgba(7,13,26,.85);
      backdrop-filter:blur(6px); z-index:9000;
      display:flex; align-items:center; justify-content:center;
      padding:20px; animation:fadeIn .2s ease;
    `;

    this.dialog = document.createElement('div');
    this.dialog.style.cssText = `
      background:#0e1729; border:1px solid #172035; border-radius:16px;
      width:100%; max-width:${widths[size]}; max-height:90vh;
      display:flex; flex-direction:column; animation:slideUp .25s ease;
      font-family:'DM Sans',sans-serif;
    `;

    this.dialog.innerHTML = `
      <div style="padding:22px 26px; border-bottom:1px solid #172035; display:flex; align-items:center; justify-content:space-between; flex-shrink:0;">
        <h3 style="margin:0; font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:700; color:#e2e8f4">${title}</h3>
        <button class="aq-modal-close" style="background:none;border:none;color:#5a7295;cursor:pointer;font-size:1.3rem;line-height:1;padding:4px">×</button>
      </div>
      <div class="aq-modal-body" style="padding:26px; overflow-y:auto; flex:1; color:#e2e8f4">
        ${typeof body === 'string' ? body : ''}
      </div>
      ${footer ? `<div style="padding:16px 26px; border-top:1px solid #172035; display:flex; justify-content:flex-end; gap:10px; flex-shrink:0">${footer}</div>` : ''}
    `;

    if (typeof body !== 'string') {
      this.dialog.querySelector('.aq-modal-body').appendChild(body);
    }

    this.overlay.appendChild(this.dialog);
    document.body.appendChild(this.overlay);

    // Close handlers
    this.overlay.querySelector('.aq-modal-close').addEventListener('click', () => this.close());
    this.overlay.addEventListener('click', (e) => { if (e.target === this.overlay) this.close(); });
    document.addEventListener('keydown', this._escHandler = (e) => { if (e.key === 'Escape') this.close(); });

    if (!document.getElementById('aq-modal-anim')) {
      const s = document.createElement('style');
      s.id = 'aq-modal-anim';
      s.textContent = `
        @keyframes fadeIn { from{opacity:0} to{opacity:1} }
        @keyframes slideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:none} }
      `;
      document.head.appendChild(s);
    }
  }

  setBody(html) {
    const body = this.overlay.querySelector('.aq-modal-body');
    if (typeof html === 'string') body.innerHTML = html;
    else { body.innerHTML = ''; body.appendChild(html); }
  }

  close() {
    document.removeEventListener('keydown', this._escHandler);
    this.overlay.style.animation = 'fadeIn .2s ease reverse';
    setTimeout(() => { this.overlay.remove(); this.onClose?.(); }, 180);
  }

  static confirm({ title, message, confirmText = 'Confirmar', danger = false }) {
    return new Promise((resolve) => {
      const footer = `
        <button id="modal-cancel-btn" style="background:rgba(255,255,255,.05);border:1px solid #172035;border-radius:8px;padding:9px 20px;color:#8ba3c7;font-family:'DM Sans',sans-serif;cursor:pointer;">Cancelar</button>
        <button id="modal-confirm-btn" style="background:${danger ? 'linear-gradient(135deg,#f43f5e,#e11d48)' : 'linear-gradient(135deg,#00d4ff,#0ea5e9)'};border:none;border-radius:8px;padding:9px 20px;color:${danger ? '#fff' : '#051020'};font-family:'DM Sans',sans-serif;font-weight:600;cursor:pointer;">${confirmText}</button>
      `;
      const m = new Modal({ title, body: `<p style="margin:0;color:#8ba3c7;line-height:1.6">${message}</p>`, footer });
      m.overlay.querySelector('#modal-cancel-btn').addEventListener('click', () => { m.close(); resolve(false); });
      m.overlay.querySelector('#modal-confirm-btn').addEventListener('click', () => { m.close(); resolve(true); });
    });
  }
}

// ─────────────────────────────────────────────
// Dynamic Table
// ─────────────────────────────────────────────
export class DataTable {
  constructor(container, { columns, fetchFn, actions = [], pageSize = 20, searchable = true, filters = [] }) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.columns = columns;
    this.fetchFn = fetchFn;
    this.actions = actions;
    this.pageSize = pageSize;
    this.searchable = searchable;
    this.filters = filters;
    this.currentPage = 1;
    this.search = '';
    this.filterValues = {};
    this.totalCount = 0;

    this._render();
    this.load();
  }

  _render() {
    this.container.innerHTML = `
      <div class="aq-table-toolbar" style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
        ${this.searchable ? `
          <div style="position:relative;flex:1;min-width:200px">
            <span style="position:absolute;left:12px;top:50%;transform:translateY(-50%);color:#5a7295;font-size:.9rem">🔍</span>
            <input type="text" class="aq-search" placeholder="Pesquisar..." style="
              width:100%;background:#0e1729;border:1px solid #172035;border-radius:8px;
              padding:9px 12px 9px 36px;color:#e2e8f4;font-family:'DM Sans',sans-serif;
              font-size:.85rem;outline:none;
            ">
          </div>
        ` : ''}
        ${this.filters.map(f => `
          <select class="aq-filter" data-key="${f.key}" style="
            background:#0e1729;border:1px solid #172035;border-radius:8px;
            padding:9px 12px;color:#e2e8f4;font-family:'DM Sans',sans-serif;font-size:.85rem;outline:none;
          ">
            <option value="">${f.label}</option>
            ${f.options.map(o => `<option value="${o.value}">${o.label}</option>`).join('')}
          </select>
        `).join('')}
        <button class="aq-refresh-btn" style="
          background:#172035;border:1px solid #1e2d45;border-radius:8px;
          padding:9px 14px;color:#8ba3c7;cursor:pointer;font-size:.85rem;
        ">↻</button>
      </div>

      <div class="aq-table-wrap" style="overflow-x:auto;border-radius:10px;border:1px solid #172035">
        <table style="width:100%;border-collapse:collapse;font-family:'DM Sans',sans-serif">
          <thead>
            <tr style="background:#111827">
              ${this.columns.map(c => `
                <th style="padding:11px 16px;text-align:left;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:#6b7fa3;font-weight:600;border-bottom:1px solid #172035;white-space:nowrap">
                  ${c.label}
                </th>
              `).join('')}
              ${this.actions.length ? `<th style="padding:11px 16px;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:#6b7fa3;font-weight:600;border-bottom:1px solid #172035;text-align:right">Ações</th>` : ''}
            </tr>
          </thead>
          <tbody class="aq-tbody">
            <tr><td colspan="${this.columns.length + (this.actions.length ? 1 : 0)}" style="padding:40px;text-align:center;color:#5a7295">
              <div style="width:24px;height:24px;border:2px solid rgba(0,212,255,.2);border-top-color:#00d4ff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px"></div>
              Carregando...
            </td></tr>
          </tbody>
        </table>
      </div>

      <div class="aq-pagination" style="display:flex;align-items:center;justify-content:space-between;margin-top:14px;font-size:.8rem;color:#5a7295;flex-wrap:wrap;gap:8px">
        <span class="aq-page-info"></span>
        <div style="display:flex;gap:6px" class="aq-page-btns"></div>
      </div>
    `;

    // Events
    this.container.querySelector('.aq-search')?.addEventListener('input', (e) => {
      clearTimeout(this._searchTimer);
      this._searchTimer = setTimeout(() => {
        this.search = e.target.value;
        this.currentPage = 1;
        this.load();
      }, 400);
    });

    this.container.querySelectorAll('.aq-filter').forEach(sel => {
      sel.addEventListener('change', () => {
        this.filterValues[sel.dataset.key] = sel.value;
        this.currentPage = 1;
        this.load();
      });
    });

    this.container.querySelector('.aq-refresh-btn')?.addEventListener('click', () => this.load());
  }

  async load() {
    const tbody = this.container.querySelector('.aq-tbody');
    const cols = this.columns.length + (this.actions.length ? 1 : 0);

    tbody.innerHTML = `<tr><td colspan="${cols}" style="padding:40px;text-align:center;color:#5a7295">
      <div style="width:24px;height:24px;border:2px solid rgba(0,212,255,.2);border-top-color:#00d4ff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px"></div>
      Carregando...
    </td></tr>`;

    try {
      const params = {
        page: this.currentPage,
        page_size: this.pageSize,
        ...(this.search ? { search: this.search } : {}),
        ...this.filterValues,
      };

      const data = await this.fetchFn(params);
      const results = data?.results || (Array.isArray(data) ? data : []);
      this.totalCount = data?.count || results.length;

      if (!results.length) {
        tbody.innerHTML = `<tr><td colspan="${cols}" style="padding:40px;text-align:center;color:#5a7295">
          <div style="font-size:2rem;margin-bottom:8px;opacity:.3">📋</div>
          Nenhum resultado encontrado.
        </td></tr>`;
        this._updatePagination(0);
        return;
      }

      tbody.innerHTML = results.map((row, i) => `
        <tr style="border-bottom:1px solid rgba(23,32,53,.8);transition:background .15s;cursor:default"
            onmouseover="this.style.background='rgba(0,212,255,.03)'"
            onmouseout="this.style.background=''"
        >
          ${this.columns.map(c => `
            <td style="padding:12px 16px;font-size:.84rem;color:#c8d8f0;vertical-align:middle">
              ${c.render ? c.render(row[c.key], row) : (row[c.key] ?? '—')}
            </td>
          `).join('')}
          ${this.actions.length ? `
            <td style="padding:12px 16px;text-align:right;white-space:nowrap">
              <div style="display:flex;justify-content:flex-end;gap:6px">
                ${this.actions.map(a => `
                  <button
                    data-action="${a.key}"
                    data-index="${i}"
                    title="${a.label}"
                    style="
                      background:${a.danger ? 'rgba(244,63,94,.08)' : 'rgba(0,212,255,.06)'};
                      border:1px solid ${a.danger ? 'rgba(244,63,94,.2)' : 'rgba(0,212,255,.15)'};
                      border-radius:6px; padding:5px 10px;
                      color:${a.danger ? '#f43f5e' : '#00d4ff'};
                      font-size:.75rem; cursor:pointer;
                    "
                  >${a.icon || ''} ${a.label}</button>
                `).join('')}
              </div>
            </td>
          ` : ''}
        </tr>
      `).join('');

      // Bind action events
      tbody.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
          const action = this.actions.find(a => a.key === btn.dataset.action);
          const row = results[parseInt(btn.dataset.index)];
          action?.handler?.(row);
        });
      });

      this._updatePagination(this.totalCount);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="${cols}" style="padding:40px;text-align:center;color:#f43f5e">
        Erro ao carregar dados: ${err.message}
      </td></tr>`;
    }
  }

  _updatePagination(total) {
    const totalPages = Math.ceil(total / this.pageSize);
    const start = (this.currentPage - 1) * this.pageSize + 1;
    const end = Math.min(this.currentPage * this.pageSize, total);

    const info = this.container.querySelector('.aq-page-info');
    const btns = this.container.querySelector('.aq-page-btns');

    info.textContent = total ? `${start}–${end} de ${total}` : '0 resultados';

    const btnStyle = (active) => `
      background:${active ? 'linear-gradient(135deg,#00d4ff,#0ea5e9)' : '#0e1729'};
      border:1px solid ${active ? 'transparent' : '#172035'};
      border-radius:6px; padding:5px 10px;
      color:${active ? '#051020' : '#8ba3c7'}; font-size:.8rem;
      cursor:pointer; font-family:'DM Sans',sans-serif; font-weight:${active ? '600' : '400'};
    `;

    const pages = [];
    for (let i = 1; i <= Math.min(totalPages, 7); i++) pages.push(i);
    if (totalPages > 7 && !pages.includes(totalPages)) pages.push('...', totalPages);

    btns.innerHTML = `
      <button ${this.currentPage <= 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}"
        style="${btnStyle(false)} ${this.currentPage <= 1 ? 'opacity:.4;cursor:not-allowed' : ''}">‹</button>
      ${pages.map(p => p === '...'
        ? `<span style="padding:5px 4px;color:#5a7295">…</span>`
        : `<button data-page="${p}" style="${btnStyle(p === this.currentPage)}">${p}</button>`
      ).join('')}
      <button ${this.currentPage >= totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}"
        style="${btnStyle(false)} ${this.currentPage >= totalPages ? 'opacity:.4;cursor:not-allowed' : ''}">›</button>
    `;

    btns.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.currentPage = parseInt(btn.dataset.page);
        this.load();
      });
    });
  }

  reload() { this.load(); }
}

// ─────────────────────────────────────────────
// Dynamic Form
// ─────────────────────────────────────────────
export class DynamicForm {
  constructor(container, { fields, onSubmit, submitLabel = 'Salvar' }) {
    this.container = typeof container === 'string' ? document.querySelector(container) : container;
    this.fields = fields;
    this.onSubmit = onSubmit;
    this.submitLabel = submitLabel;
    this._render();
  }

  _render() {
    const fieldHTML = this.fields.map(f => {
      const base = `id="${f.key}" name="${f.key}"
        ${f.required ? 'required' : ''}
        ${f.value !== undefined ? `value="${f.value}"` : ''}
        style="width:100%;background:#0e1729;border:1px solid #172035;border-radius:8px;
               padding:11px 14px;color:#e2e8f4;font-family:'DM Sans',sans-serif;
               font-size:.875rem;outline:none;transition:border-color .2s"
        onfocus="this.style.borderColor='#00d4ff';this.style.boxShadow='0 0 0 3px rgba(0,212,255,.1)'"
        onblur="this.style.borderColor='#172035';this.style.boxShadow='none'"
      `;

      let input;
      if (f.type === 'select') {
        input = `<select ${base} ${f.multiple ? 'multiple' : ''}>
          ${f.placeholder ? `<option value="">-- ${f.placeholder} --</option>` : ''}
          ${(f.options || []).map(o => `<option value="${o.value}" ${f.value == o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>`;
      } else if (f.type === 'textarea') {
        input = `<textarea ${base} rows="${f.rows || 3}" placeholder="${f.placeholder || ''}">${f.value || ''}</textarea>`;
      } else if (f.type === 'checkbox') {
        input = `<label style="display:flex;align-items:center;gap:10px;color:#8ba3c7;cursor:pointer">
          <input type="checkbox" id="${f.key}" name="${f.key}" ${f.value ? 'checked' : ''} style="accent-color:#00d4ff;width:16px;height:16px">
          ${f.checkLabel || f.label}
        </label>`;
      } else {
        input = `<input type="${f.type || 'text'}" placeholder="${f.placeholder || ''}" ${base}>`;
      }

      return `
        <div class="aq-field" data-key="${f.key}" style="margin-bottom:18px">
          ${f.type !== 'checkbox' ? `<label for="${f.key}" style="display:block;font-size:.75rem;font-weight:600;color:#6b8ab5;letter-spacing:.06em;text-transform:uppercase;margin-bottom:7px">
            ${f.label}${f.required ? ' <span style="color:#f43f5e">*</span>' : ''}
          </label>` : ''}
          ${input}
          <div class="aq-field-error" style="display:none;margin-top:5px;font-size:.78rem;color:#f43f5e"></div>
          ${f.hint ? `<div style="margin-top:4px;font-size:.75rem;color:#5a7295">${f.hint}</div>` : ''}
        </div>
      `;
    }).join('');

    this.container.innerHTML = `
      <form class="aq-form" novalidate>
        ${fieldHTML}
        <div class="aq-form-error" style="display:none;background:rgba(244,63,94,.08);border:1px solid rgba(244,63,94,.2);border-radius:8px;padding:12px;margin-bottom:16px;font-size:.82rem;color:#f43f5e"></div>
        <button type="submit" class="aq-submit-btn" style="
          background:linear-gradient(135deg,#00d4ff,#0ea5e9);border:none;border-radius:8px;
          padding:12px 28px;color:#051020;font-family:'DM Sans',sans-serif;
          font-size:.9rem;font-weight:700;cursor:pointer;width:100%;
        ">${this.submitLabel}</button>
      </form>
    `;

    this.container.querySelector('.aq-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this._handleSubmit();
    });
  }

  async _handleSubmit() {
    this.clearErrors();
    const data = this.getData();
    const btn = this.container.querySelector('.aq-submit-btn');
    btnLoading(btn, true);

    try {
      await this.onSubmit(data);
    } catch (err) {
      if (err.isValidation && typeof err.data === 'object') {
        this.setErrors(err.data);
      } else {
        const errBox = this.container.querySelector('.aq-form-error');
        errBox.style.display = 'block';
        errBox.innerHTML = err.getMessages?.().join('<br>') || err.message;
      }
    } finally {
      btnLoading(btn, false);
    }
  }

  getData() {
    const form = this.container.querySelector('.aq-form');
    const fd = new FormData(form);
    const data = {};
    this.fields.forEach(f => {
      if (f.type === 'checkbox') {
        data[f.key] = form.querySelector(`[name="${f.key}"]`)?.checked || false;
      } else if (f.type === 'number') {
        data[f.key] = fd.get(f.key) ? Number(fd.get(f.key)) : null;
      } else {
        data[f.key] = fd.get(f.key) || '';
      }
    });
    return data;
  }

  setErrors(errors) {
    Object.entries(errors).forEach(([key, msgs]) => {
      const field = this.container.querySelector(`[data-key="${key}"]`);
      if (field) {
        const errEl = field.querySelector('.aq-field-error');
        const input = field.querySelector('input,select,textarea');
        if (errEl) { errEl.style.display = 'block'; errEl.textContent = Array.isArray(msgs) ? msgs.join(', ') : msgs; }
        if (input) input.style.borderColor = '#f43f5e';
      }
    });
  }

  clearErrors() {
    this.container.querySelectorAll('.aq-field-error').forEach(e => { e.style.display = 'none'; e.textContent = ''; });
    this.container.querySelectorAll('input,select,textarea').forEach(i => { i.style.borderColor = '#172035'; });
    const errBox = this.container.querySelector('.aq-form-error');
    if (errBox) errBox.style.display = 'none';
  }

  populate(data) {
    this.fields.forEach(f => {
      const el = this.container.querySelector(`[name="${f.key}"]`);
      if (!el) return;
      if (f.type === 'checkbox') el.checked = !!data[f.key];
      else el.value = data[f.key] ?? '';
    });
  }
}

// ─────────────────────────────────────────────
// Status badge helper
// ─────────────────────────────────────────────
export function badge(text, type = 'default') {
  const styles = {
    success:  'background:rgba(34,211,165,.12);color:#22d3a5',
    warning:  'background:rgba(245,158,11,.12);color:#f59e0b',
    danger:   'background:rgba(244,63,94,.12);color:#f43f5e',
    info:     'background:rgba(0,212,255,.12);color:#00d4ff',
    purple:   'background:rgba(168,85,247,.12);color:#a855f7',
    default:  'background:rgba(107,127,163,.12);color:#6b7fa3',
  };
  return `<span style="padding:3px 10px;border-radius:20px;font-size:.7rem;font-weight:600;letter-spacing:.04em;${styles[type] || styles.default}">${text}</span>`;
}

export function statusBadge(status) {
  const map = {
    ACTIVE:   badge('Ativo', 'success'),
    INACTIVE: badge('Inativo', 'default'),
    PAID:     badge('Pago', 'success'),
    PENDING:  badge('Pendente', 'warning'),
    OVERDUE:  badge('Vencido', 'danger'),
    CANCELLED:badge('Cancelado', 'default'),
    TRIAL:    badge('Trial', 'info'),
    SUSPENDED:badge('Suspenso', 'danger'),
    EXPIRED:  badge('Expirado', 'danger'),
    COMPLETED:badge('Concluída', 'success'),
    FAILED:   badge('Falhou', 'danger'),
    MAINTENANCE: badge('Manutenção', 'purple'),
  };
  return map[status] || badge(status);
}

export function currency(val, currency = 'MT') {
  if (val === null || val === undefined) return '—';
  return `${currency} ${Number(val).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
}

export function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('pt-BR');
}
