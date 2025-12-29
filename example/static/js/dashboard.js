/**
 * JavaScript для дашборда с графиками и аналитикой
 */

(function() {
    'use strict';
    
    let revenueChart = null;
    let usersChart = null;
    let methodsChart = null;

    // Загрузка данных для графиков
    window.loadChartData = async function(days = 30) {
        try {
            // График выручки и продаж
            const chartResponse = await fetch(`/api/metrics/chart?days=${days}`);
            if (!chartResponse.ok) {
                console.error('Ошибка загрузки данных графика:', chartResponse.status);
                return;
            }
            
            const chartData = await chartResponse.json();
            console.log('Данные графика загружены:', JSON.stringify(chartData, null, 2));
            console.log('Количество точек данных:', chartData.data ? chartData.data.length : 0);
            
            if (chartData.data && chartData.data.length > 0) {
                // Логируем первые несколько точек для отладки
                console.log('Первые 5 точек данных:', chartData.data.slice(0, 5));
                
                const labels = chartData.data.map(d => {
                    const date = new Date(d.date);
                    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
                });
                const revenueData = chartData.data.map(d => d.revenue || 0);
                const usersData = chartData.data.map(d => d.new_users || 0);
                
                console.log('Все данные для графика выручки:', revenueData);
                console.log('Все данные для графика новых пользователей:', usersData);
                console.log('Максимальная выручка:', Math.max(...revenueData));
                console.log('Максимальные новые пользователи:', Math.max(...usersData));
                console.log('Количество ненулевых значений выручки:', revenueData.filter(v => v > 0).length);
                console.log('Количество ненулевых значений пользователей:', usersData.filter(v => v > 0).length);
                
                // График выручки
                const revenueCtx = document.getElementById('revenueChart');
                if (revenueCtx && window.Chart) {
                    if (revenueChart) revenueChart.destroy();
                    revenueChart = new Chart(revenueCtx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Выручка ($)',
                                data: revenueData,
                                borderColor: 'rgb(99, 102, 241)',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                tension: 0.4,
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    labels: { color: '#a0a0b0' }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: { color: '#a0a0b0' },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                },
                                x: {
                                    ticks: { color: '#a0a0b0' },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                }
                            }
                        }
                    });
                }
                
                // График новых пользователей
                const usersCtx = document.getElementById('usersChart');
                if (usersCtx && window.Chart) {
                    if (usersChart) usersChart.destroy();
                    usersChart = new Chart(usersCtx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Новые пользователи',
                                data: usersData,
                                backgroundColor: 'rgba(16, 185, 129, 0.6)',
                                borderColor: 'rgb(16, 185, 129)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    labels: { color: '#a0a0b0' }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: { color: '#a0a0b0', stepSize: 1 },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                },
                                x: {
                                    ticks: { color: '#a0a0b0' },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                }
                            }
                        }
                    });
                }
            } else {
                console.warn('Нет данных для графика или данные пустые');
                // Создаем пустые графики, если данных нет
                const revenueCtx = document.getElementById('revenueChart');
                const salesCtx = document.getElementById('salesChart');
                
                if (revenueCtx && window.Chart) {
                    if (revenueChart) revenueChart.destroy();
                    revenueChart = new Chart(revenueCtx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Выручка ($)',
                                data: [],
                                borderColor: 'rgb(99, 102, 241)',
                                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                                tension: 0.4,
                                fill: true
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    labels: { color: '#a0a0b0' }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: { color: '#a0a0b0' },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                },
                                x: {
                                    ticks: { color: '#a0a0b0' },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                }
                            }
                        }
                    });
                }
                
                if (usersCtx && window.Chart) {
                    if (usersChart) usersChart.destroy();
                    usersChart = new Chart(usersCtx, {
                        type: 'bar',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Новые пользователи',
                                data: [],
                                backgroundColor: 'rgba(16, 185, 129, 0.6)',
                                borderColor: 'rgb(16, 185, 129)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    labels: { color: '#a0a0b0' }
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    ticks: { color: '#a0a0b0', stepSize: 1 },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                },
                                x: {
                                    ticks: { color: '#a0a0b0' },
                                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                                }
                            }
                        }
                    });
                }
            }
            
            // График выручки по методам оплаты
            const metricsResponse = await fetch('/api/metrics');
            const metrics = await metricsResponse.json();
            
            if (metrics.revenue_by_method) {
                const methodsCtx = document.getElementById('methodsChart');
                if (methodsCtx && window.Chart) {
                    if (methodsChart) methodsChart.destroy();
                    const methodLabels = Object.keys(metrics.revenue_by_method);
                    const methodData = Object.values(metrics.revenue_by_method);
                    
                    methodsChart = new Chart(methodsCtx, {
                        type: 'doughnut',
                        data: {
                            labels: methodLabels,
                            datasets: [{
                                data: methodData,
                                backgroundColor: [
                                    'rgba(99, 102, 241, 0.8)',
                                    'rgba(139, 92, 246, 0.8)',
                                    'rgba(59, 130, 246, 0.8)',
                                    'rgba(16, 185, 129, 0.8)',
                                    'rgba(245, 158, 11, 0.8)'
                                ],
                                borderColor: [
                                    'rgb(99, 102, 241)',
                                    'rgb(139, 92, 246)',
                                    'rgb(59, 130, 246)',
                                    'rgb(16, 185, 129)',
                                    'rgb(245, 158, 11)'
                                ],
                                borderWidth: 2
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: { color: '#a0a0b0', padding: 15 }
                                }
                            }
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Ошибка загрузки данных графиков:', error);
            // Показываем уведомление об ошибке
            if (window.Notification) {
                window.Notification.show('Ошибка загрузки данных графиков', 'error');
            }
        }
    };

    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', () => {
        // Загружаем Chart.js если еще не загружен
        if (!window.Chart) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            script.onload = () => {
                window.loadChartData(30);
            };
            document.head.appendChild(script);
        } else {
            window.loadChartData(30);
        }
        
        // Обновляем активную кнопку периода
        document.querySelectorAll('[onclick*="loadChartData"]').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('[onclick*="loadChartData"]').forEach(b => {
                    b.classList.remove('active');
                });
                this.classList.add('active');
            });
        });
    });
})();
