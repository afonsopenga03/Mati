/**
 * Companies API Module
 * Operações CRUD para empresas no sistema SaaS
 */

import { api } from './client.js';

export const CompaniesAPI = {
    // Listar empresas com filtros e paginação
    list(params = {}) {
        return api.get('/companies/', params);
    },

    // Obter detalhes de uma empresa
    retrieve(id) {
        return api.get(`/companies/${id}/`);
    },

    // Criar nova empresa
    create(data) {
        return api.post('/companies/', data);
    },

    // Atualizar empresa
    update(id, data) {
        return api.put(`/companies/${id}/`, data);
    },

    // Atualização parcial
    patch(id, data) {
        return api.patch(`/companies/${id}/`, data);
    },

    // Ativar/Desativar empresa
    toggleStatus(id, active) {
        return api.patch(`/companies/${id}/`, { is_active: active });
    },

    // Obter estatísticas da empresa
    getStats(id) {
        return api.get(`/companies/${id}/stats/`);
    },

    // Obter usuários da empresa
    getUsers(id, params = {}) {
        return api.get(`/companies/${id}/users/`, params);
    },

    // Obter subscrição da empresa
    getSubscription(id) {
        return api.get(`/companies/${id}/subscription/`);
    },

    // Buscar empresas (autocomplete)
    search(query) {
        return api.get('/companies/search/', { q: query });
    },

    // Exportar lista para CSV
    exportCSV(params = {}) {
        return api.get('/companies/export/csv/', params);
    },
};

export default CompaniesAPI;
