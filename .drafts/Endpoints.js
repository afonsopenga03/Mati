/**
 * AquaGest API Modules
 * All endpoint wrappers organized by domain
 */
import { api } from './client.js';

// ─────────────────────────────────────────────
// Companies (SaaS Admin)
// ─────────────────────────────────────────────
export const CompaniesAPI = {
  list:       (p) => api.get('/companies/', p),
  get:        (id) => api.get(`/companies/${id}/`),
  create:     (d) => api.post('/companies/', d),
  update:     (id, d) => api.patch(`/companies/${id}/`, d),
  activate:   (id) => api.post(`/companies/${id}/activate/`),
  deactivate: (id) => api.post(`/companies/${id}/deactivate/`),
};

// ─────────────────────────────────────────────
// Subscriptions & Plans
// ─────────────────────────────────────────────
export const PlansAPI = {
  list:   () => api.get('/subscriptions/plans/'),
  get:    (id) => api.get(`/subscriptions/plans/${id}/`),
  create: (d) => api.post('/subscriptions/plans/', d),
  update: (id, d) => api.patch(`/subscriptions/plans/${id}/`, d),
};

export const SubscriptionsAPI = {
  current:    () => api.get('/subscriptions/current/'),
  usage:      () => api.get('/subscriptions/usage/'),
  changePlan: (d) => api.post('/subscriptions/change-plan/', d),
  cancel:     () => api.post('/subscriptions/cancel/'),
  invoices:   () => api.get('/subscriptions/invoices/'),
  payInvoice: (id, d) => api.post(`/subscriptions/invoices/${id}/pay/`, d),
};

// ─────────────────────────────────────────────
// Users
// ─────────────────────────────────────────────
export const UsersAPI = {
  list:           (p) => api.get('/users/', p),
  get:            (id) => api.get(`/users/${id}/`),
  create:         (d) => api.post('/users/', d),
  update:         (id, d) => api.patch(`/users/${id}/`, d),
  delete:         (id) => api.delete(`/users/${id}/`),
  me:             () => api.get('/users/me/'),
  changePassword: (d) => api.post('/users/change-password/', d),
};

// ─────────────────────────────────────────────
// Customers
// ─────────────────────────────────────────────
export const CustomersAPI = {
  list:       (p) => api.get('/customers/', p),
  get:        (id) => api.get(`/customers/${id}/`),
  create:     (d) => api.post('/customers/', d),
  update:     (id, d) => api.patch(`/customers/${id}/`, d),
  deactivate: (id) => api.post(`/customers/${id}/deactivate/`),
  addresses:  (id) => api.get(`/customers/${id}/addresses/`),
  addAddress: (id, d) => api.post(`/customers/${id}/addresses/`, d),
};

// ─────────────────────────────────────────────
// Meters
// ─────────────────────────────────────────────
export const MetersAPI = {
  list:               (p) => api.get('/meters/', p),
  get:                (id) => api.get(`/meters/${id}/`),
  create:             (d) => api.post('/meters/', d),
  update:             (id, d) => api.patch(`/meters/${id}/`, d),
  setMaintenance:     (id) => api.post(`/meters/${id}/set-maintenance/`),
  setActive:          (id) => api.post(`/meters/${id}/set-active/`),
  readings:           (id, p) => api.get(`/meters/${id}/readings/`, p),
  addReading:         (id, d) => api.post(`/meters/${id}/readings/`, d),
  consumptionHistory: (id, p) => api.get(`/meters/${id}/consumption-history/`, p),
  anomalies:          (p) => api.get('/meters/anomalies/', p),
};

// ─────────────────────────────────────────────
// Billing
// ─────────────────────────────────────────────
export const BillingAPI = {
  tariffs: {
    list:   (p) => api.get('/tariffs/', p),
    get:    (id) => api.get(`/tariffs/${id}/`),
    create: (d) => api.post('/tariffs/', d),
    update: (id, d) => api.patch(`/tariffs/${id}/`, d),
  },
  invoices: {
    list:          (p) => api.get('/invoices/', p),
    get:           (id) => api.get(`/invoices/${id}/`),
    create:        (d) => api.post('/invoices/', d),
    markPaid:      (id) => api.post(`/invoices/${id}/mark-paid/`),
    cancel:        (id) => api.post(`/invoices/${id}/cancel/`),
    summary:       () => api.get('/invoices/summary/'),
    generate:      (d) => api.post('/invoices/generate/', d),
    applyLateFees: () => api.post('/invoices/apply-late-fees/'),
  },
};

// ─────────────────────────────────────────────
// Payments
// ─────────────────────────────────────────────
export const PaymentsAPI = {
  list:      (p) => api.get('/payments/', p),
  get:       (id) => api.get(`/payments/${id}/`),
  create:    (d) => api.post('/payments/', d),
  reverse:   (id, d) => api.post(`/payments/${id}/reverse/`, d),
  byInvoice: (invId) => api.get(`/payments/by-invoice/${invId}/`),
  summary:   () => api.get('/payments/summary/'),
};

// ─────────────────────────────────────────────
// Field Work
// ─────────────────────────────────────────────
export const FieldAPI = {
  routes: {
    list:          (p) => api.get('/routes/', p),
    get:           (id) => api.get(`/routes/${id}/`),
    create:        (d) => api.post('/routes/', d),
    update:        (id, d) => api.patch(`/routes/${id}/`, d),
    addStop:       (id, d) => api.post(`/routes/${id}/add-stop/`, d),
    reorder:       (id, d) => api.post(`/routes/${id}/reorder/`, d),
    generateTasks: (id, p) => api.get(`/routes/${id}/generate-tasks/`, p),
  },
  tasks: {
    list:         (p) => api.get('/field-tasks/', p),
    get:          (id) => api.get(`/field-tasks/${id}/`),
    create:       (d) => api.post('/field-tasks/', d),
    myTasks:      (p) => api.get('/field-tasks/my-tasks/', p),
    bundle:       () => api.get('/field-tasks/bundle/'),
    sync:         (d) => api.post('/field-tasks/sync/', d),
    start:        (id) => api.post(`/field-tasks/${id}/start/`),
    complete:     (id, d) => api.post(`/field-tasks/${id}/complete/`, d),
    skip:         (id, d) => api.post(`/field-tasks/${id}/skip/`, d),
    productivity: () => api.get('/field-tasks/productivity/'),
  },
};
