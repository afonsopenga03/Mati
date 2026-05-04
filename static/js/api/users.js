/**
 * Users API Module
 * Gestão de utilizadores do sistema
 */

import { api } from './client.js';

export const UsersAPI = {
    // Listar usuários
    list(params = {}) {
        return api.get('/saas-admin/users/', params);
    },

    // Obter detalhes
    retrieve(id) {
        return api.get(`/saas-admin/users/${id}/`);
    },

    // Criar usuário
    create(data) {
        return api.post('/saas-admin/users/', data);
    },

    // Atualizar usuário
    update(id, data) {
        return api.put(`/saas-admin/users/${id}/`, data);
    },

    // Atualização parcial
    patch(id, data) {
        return api.patch(`/saas-admin/users/${id}/`, data);
    },

    // Excluir usuário
    delete(id) {
        return api.delete(`/saas-admin/users/${id}/`);
    },

    // Ativar/Desativar
    toggleStatus(id, isActive) {
        return api.patch(`/saas-admin/users/${id}/`, { is_active: isActive });
    },

    // Resetar senha
    resetPassword(id, data = {}) {
        return api.post(`/saas-admin/users/${id}/reset-password/`, data);
    },

    // Alterar permissões/roles
    updatePermissions(id, permissions) {
        return api.patch(`/saas-admin/users/${id}/permissions/`, { permissions });
    },

    // Atribuir a empresa
    assignToCompany(userId, companyId, role = 'member') {
        return api.post(`/saas-admin/users/${userId}/assign-company/`, {
            company_id: companyId,
            role
        });
    },

    // Remover da empresa
    removeFromCompany(userId, companyId) {
        return api.delete(`/saas-admin/users/${userId}/companies/${companyId}/`);
    },

    // Obter empresas do usuário
    getCompanies(userId, params = {}) {
        return api.get(`/saas-admin/users/${userId}/companies/`, params);
    },

    // Login como usuário (impersonate)
    impersonate(userId) {
        return api.post(`/saas-admin/users/${userId}/impersonate/`);
    },

    // Estatísticas do usuário
    getStats(userId) {
        return api.get(`/saas-admin/users/${userId}/stats/`);
    },

    // Atividades/log do usuário
    getActivities(userId, params = {}) {
        return api.get(`/saas-admin/users/${userId}/activities/`, params);
    },

    // Busca/autocomplete
    search(query, params = {}) {
        return api.get('/saas-admin/users/search/', { q: query, ...params });
    },

    // Exportar lista
    exportCSV(params = {}) {
        return api.get('/saas-admin/users/export/csv/', params);
    },
};

export default UsersAPI;
