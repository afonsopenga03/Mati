/**
 * Subscriptions API Module
 * Gestão de subscrições das empresas
 */

import { api } from './client.js';

export const SubscriptionsAPI = {
    // Listar subscrições
    list(params = {}) {
        return api.get('/saas-admin/subscriptions/', params);
    },

    // Obter detalhes
    retrieve(id) {
        return api.get(`/saas-admin/subscriptions/${id}/`);
    },

    // Criar subscrição
    create(data) {
        return api.post('/saas-admin/subscriptions/', data);
    },

    // Atualizar
    update(id, data) {
        return api.put(`/saas-admin/subscriptions/${id}/`, data);
    },

    // Atualização parcial
    patch(id, data) {
        return api.patch(`/saas-admin/subscriptions/${id}/`, data);
    },

    // Cancelar subscrição
    cancel(id, data = {}) {
        return api.post(`/saas-admin/subscriptions/${id}/cancel/`, data);
    },

    // Reativar subscrição
    reactivate(id, data = {}) {
        return api.post(`/saas-admin/subscriptions/${id}/reactivate/`, data);
    },

    // Upgrade/Downgrade de plano
    changePlan(id, data) {
        return api.post(`/saas-admin/subscriptions/${id}/change-plan/`, data);
    },

    // Pausar subscrição
    pause(id, reason = '') {
        return api.post(`/saas-admin/subscriptions/${id}/pause/`, { reason });
    },

    // Retomar subscrição
    resume(id) {
        return api.post(`/saas-admin/subscriptions/${id}/resume/`);
    },

    // Obter subscrição atual de uma empresa
    getCurrent(companyId) {
        return api.get(`/saas-admin/companies/${companyId}/subscription/`);
    },

    // Histórico de mudanças
    getHistory(id, params = {}) {
        return api.get(`/saas-admin/subscriptions/${id}/history/`, params);
    },

    // Próximas renovações
    getUpcomingRenewals(params = {}) {
        return api.get('/saas-admin/subscriptions/upcoming-renewals/', params);
    },

    // Subscrições expirando
    getExpiring(days = 30) {
        return api.get('/saas-admin/subscriptions/expiring/', { days });
    },

    // Estatísticas gerais
    getStats() {
        return api.get('/saas-admin/subscriptions/stats/');
    },
};

export default SubscriptionsAPI;
