/**
 * Plans API Module
 * Gestão de planos de subscrição
 */

import { api } from './client.js';

export const PlansAPI = {
    // Listar planos
    list(params = {}) {
        return api.get('/saas-admin/plans/', params);
    },

    // Obter detalhes
    retrieve(id) {
        return api.get(`/saas-admin/plans/${id}/`);
    },

    // Criar plano
    create(data) {
        return api.post('/saas-admin/plans/', data);
    },

    // Atualizar plano completo
    update(id, data) {
        return api.put(`/saas-admin/plans/${id}/`, data);
    },

    // Atualização parcial
    patch(id, data) {
        return api.patch(`/saas-admin/plans/${id}/`, data);
    },

    // Excluir plano
    delete(id) {
        return api.delete(`/saas-admin/plans/${id}/`);
    },

    // Ativar/Desativar
    toggleStatus(id, active) {
        return api.patch(`/saas-admin/plans/${id}/`, { is_active: active });
    },

    // Duplicar plano
    duplicate(id, data = {}) {
        return api.post(`/saas-admin/plans/${id}/duplicate/`, data);
    },

    // Obter estatísticas do plano
    getStats(id) {
        return api.get(`/saas-admin/plans/${id}/stats/`);
    },

    // Obter empresas com este plano
    getCompanies(id, params = {}) {
        return api.get(`/saas-admin/plans/${id}/companies/`, params);
    },

    // Verificar se pode excluir
    canDelete(id) {
        return api.get(`/saas-admin/plans/${id}/can-delete/`);
    },

    // Planos populares (para dashboard)
    getPopular() {
        return api.get('/saas-admin/plans/popular/');
    },
};

export default PlansAPI;
