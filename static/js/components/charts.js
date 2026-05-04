/**
 * Charts Module - Water Management System
 * Configuração centralizada para gráficos com Chart.js
 */

// Configurações globais do Chart.js
Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.color = '#6c757d';
Chart.defaults.scale.grid.color = 'rgba(0, 0, 0, 0.05)';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(33, 37, 41, 0.9)';
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;

// Paleta de cores do sistema
export const CHART_COLORS = {
    primary: '#0d6efd',
    success: '#198754',
    warning: '#ffc107',
    danger: '#dc3545',
    info: '#0dcaf0',
    secondary: '#6c757d',
    dark: '#212529',
    gradient: {
        primary: ['rgba(13, 110, 253, 0.8)', 'rgba(13, 110, 253, 0.1)'],
        success: ['rgba(25, 135, 84, 0.8)', 'rgba(25, 135, 84, 0.1)'],
    }
};

// Factory para criar gradientes
function createGradient(ctx, area, colors) {
    const gradient = ctx.createLinearGradient(0, area.bottom, 0, area.top);
    gradient.addColorStop(0, colors[1]);
    gradient.addColorStop(1, colors[0]);
    return gradient;
}

// Chart: Crescimento de Empresas (Line)
export function createGrowthChart(canvas, data = {}) {
    const ctx = canvas.getContext('2d');
    const area = canvas.getBoundingClientRect();

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
            datasets: [{
                label: 'Novas Empresas',
                data: data.values || [12, 19, 15, 25, 22, 30],
                borderColor: CHART_COLORS.primary,
                backgroundColor: createGradient(ctx, area, CHART_COLORS.gradient.primary),
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#fff',
                pointBorderColor: CHART_COLORS.primary,
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: (ctx) => ` ${ctx.parsed.y} empresas`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 10 },
                    grid: { borderDash: [5, 5] }
                },
                x: {
                    grid: { display: false }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// Chart: Receita por Plano (Doughnut)
export function createRevenueByPlanChart(canvas, data = {}) {
    const ctx = canvas.getContext('2d');

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || ['Free', 'Básico', 'Pro', 'Enterprise'],
            datasets: [{
                data: data.values || [15, 25, 45, 15],
                backgroundColor: [
                    CHART_COLORS.secondary,
                    CHART_COLORS.info,
                    CHART_COLORS.primary,
                    CHART_COLORS.dark
                ],
                borderWidth: 0,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const percent = ((ctx.parsed / total) * 100).toFixed(1);
                            return ` ${ctx.label}: ${percent}%`;
                        }
                    }
                }
            }
        }
    });
}

// Chart: Consumo de Água (Bar)
export function createWaterConsumptionChart(canvas, data = {}) {
    const ctx = canvas.getContext('2d');

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            datasets: [{
                label: 'Consumo (m³)',
                data: data.values || [45, 52, 38, 65, 48, 30, 25],
                backgroundColor: CHART_COLORS.info,
                borderColor: CHART_COLORS.info,
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false,
            }, {
                label: 'Meta (m³)',
                data: data.targets || [50, 50, 50, 50, 50, 35, 35],
                type: 'line',
                borderColor: CHART_COLORS.warning,
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { usePointStyle: true }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: (v) => v + 'm³' }
                }
            }
        }
    });
}

// Chart: Status de Faturas (Pie)
export function createInvoiceStatusChart(canvas, data = {}) {
    const ctx = canvas.getContext('2d');

    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels || ['Pagas', 'Pendentes', 'Atrasadas', 'Canceladas'],
            datasets: [{
                data: data.values || [65, 20, 10, 5],
                backgroundColor: [
                    CHART_COLORS.success,
                    CHART_COLORS.warning,
                    CHART_COLORS.danger,
                    CHART_COLORS.secondary
                ],
                borderWidth: 0,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => ` ${ctx.label}: ${ctx.parsed}`
                    }
                }
            }
        }
    });
}

// Inicialização automática para elementos com data-chart
export function initAutoCharts() {
    document.querySelectorAll('[data-chart]').forEach(canvas => {
        const type = canvas.dataset.chart;
        const data = canvas.dataset.chartData ? JSON.parse(canvas.dataset.chartData) : {};

        switch(type) {
            case 'growth':
                return createGrowthChart(canvas, data);
            case 'revenue':
                return createRevenueByPlanChart(canvas, data);
            case 'consumption':
                return createWaterConsumptionChart(canvas, data);
            case 'invoices':
                return createInvoiceStatusChart(canvas, data);
        }
    });
}

// Helper: Atualizar dados de um chart existente
export function updateChart(chart, newLabels, newValues) {
    chart.data.labels = newLabels;
    chart.data.datasets[0].data = newValues;
    chart.update('active');
}

// Helper: Destroy chart para evitar memory leaks
export function destroyChart(chart) {
    if (chart) {
        chart.destroy();
    }
}

// Export default com todas as funções
export default {
    createGrowthChart,
    createRevenueByPlanChart,
    createWaterConsumptionChart,
    createInvoiceStatusChart,
    initAutoCharts,
    updateChart,
    destroyChart,
    COLORS: CHART_COLORS
};
