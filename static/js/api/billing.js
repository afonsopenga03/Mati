/**
 * Billing API Module
 * Operações de faturação, faturas e pagamentos
 */

import { api } from './client.js';

export const BillingAPI = {
    // Faturas (Invoices)
    invoices: {
        list(params = {}) {
            return api.get('/billing/invoices/', params);
        },

        retrieve(id) {
            return api.get(`/billing/invoices/${id}/`);
        },

        create(data) {
            return api.post('/billing/invoices/', data);
        },

        update(id, data) {
            return api.put(`/billing/invoices/${id}/`, data);
        },

        patch(id, data) {
            return api.patch(`/billing/invoices/${id}/`, data);
        },

        delete(id) {
            return api.delete(`/billing/invoices/${id}/`);
        },

        // Gerar fatura
        generate(companyId, data) {
            return api.post(`/billing/companies/${companyId}/invoices/generate/`, data);
        },

        // Enviar fatura por email
        send(id, emails = []) {
            return api.post(`/billing/invoices/${id}/send/`, { emails });
        },

        // Download PDF
        downloadPDF(id) {
            return api.get(`/billing/invoices/${id}/pdf/`, {
                headers: { 'Accept': 'application/pdf' },
                responseType: 'blob'
            });
        },

        // Marcar como paga
        markAsPaid(id, data = {}) {
            return api.post(`/billing/invoices/${id}/mark-paid/`, data);
        },

        // Cancelar fatura
        cancel(id, reason = '') {
            return api.post(`/billing/invoices/${id}/cancel/`, { reason });
        },
    },

    // Pagamentos
    payments: {
        list(params = {}) {
            return api.get('/billing/payments/', params);
        },

        retrieve(id) {
            return api.get(`/billing/payments/${id}/`);
        },

        create(data) {
            return api.post('/billing/payments/', data);
        },

        // Processar pagamento
        process(invoiceId, data) {
            return api.post(`/billing/invoices/${invoiceId}/payments/`, data);
        },

        // Confirmar pagamento
        confirm(id, data = {}) {
            return api.post(`/billing/payments/${id}/confirm/`, data);
        },

        // Reembolsar
        refund(id, reason = '') {
            return api.post(`/billing/payments/${id}/refund/`, { reason });
        },
    },

    // Tarifas
    tariffs: {
        list(params = {}) {
            return api.get('/billing/tariffs/', params);
        },

        retrieve(id) {
            return api.get(`/billing/tariffs/${id}/`);
        },

        create(data) {
            return api.post('/billing/tariffs/', data);
        },

        update(id, data) {
            return api.put(`/billing/tariffs/${id}/`, data);
        },

        patch(id, data) {
            return api.patch(`/billing/tariffs/${id}/`, data);
        },

        delete(id) {
            return api.delete(`/billing/tariffs/${id}/`);
        },

        // Ativar/Desativar
        toggle(id, active) {
            return api.patch(`/billing/tariffs/${id}/`, { is_active: active });
        },
    },

    // Histórico de faturação SaaS
    saasBilling: {
        history(params = {}) {
            return api.get('/saas-admin/billing/history/', params);
        },

        revenue(params = {}) {
            return api.get('/saas-admin/billing/revenue/', params);
        },

        exportCSV(params = {}) {
            return api.get('/saas-admin/billing/export/csv/', params);
        },
    },

    // Estatísticas
    getStats(companyId = null) {
        const endpoint = companyId
            ? `/billing/companies/${companyId}/stats/`
            : '/billing/stats/';
        return api.get(endpoint);
    },

    // Resumo mensal
    getMonthlySummary(year, month, companyId = null) {
        const params = { year, month };
        if (companyId) params.company = companyId;
        return api.get('/billing/monthly-summary/', params);
    },
};

export default BillingAPI;
