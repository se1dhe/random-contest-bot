/**
 * JavaScript для страницы заказов на разработку
 */

let orders = [];
let currentFilter = null;

function formatOrderDescription(description, orderId) {
    if (!description) return 'Нет описания';
    
    const fileIdMatch = description.match(/FILE_ID:([A-Za-z0-9_-]+)/);
    if (fileIdMatch) {
        const fileInfoMatch = description.match(/Прикреплён файл: ([^\n]+)/);
        const fileName = fileInfoMatch ? fileInfoMatch[1].trim() : 'Файл';
        
        let displayText = description.replace(/📎 FILE_ID:[^\n]+/g, '').trim();
        if (!displayText || displayText === 'Нет описания') {
            displayText = 'Файл прикреплен';
        }
        
        return `
            <div class="space-y-2">
                <div>${Utils.escapeHtml(displayText)}</div>
                <div class="flex items-center gap-2 mt-2">
                    <a href="/api/custom-orders/${orderId}/file" 
                       class="btn btn-primary btn-sm"
                       download>
                        Скачать файл: ${Utils.escapeHtml(fileName)}
                    </a>
                </div>
            </div>
        `;
    }
    
    return Utils.escapeHtml(description);
}

async function loadOrders(status = null) {
    currentFilter = status;
    const url = status ? `/api/custom-orders?status=${status}` : '/api/custom-orders';
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        orders = data.orders;
        renderOrders();
    } catch (error) {
        console.error('Ошибка загрузки заказов:', error);
        const tbody = document.getElementById('ordersTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-error">Ошибка загрузки заказов</td></tr>';
        }
    }
}

function renderOrders() {
    const tbody = document.getElementById('ordersTableBody');
    if (!tbody) return;
    
    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-secondary">Нет заказов</td></tr>';
        return;
    }
    
    const statusColors = {
        'pending': 'badge-warning',
        'paid': 'badge-success',
        'in_progress': 'badge-info',
        'completed': 'badge-primary',
        'cancelled': 'badge-error'
    };
    
    const statusTexts = {
        'pending': 'Ожидает оплаты',
        'paid': 'Оплачен',
        'in_progress': 'В разработке',
        'completed': 'Завершён',
        'cancelled': 'Отменён'
    };
    
    tbody.innerHTML = orders.map(order => {
        const date = new Date(order.created_at).toLocaleDateString('ru-RU');
        
        return `
        <tr>
            <td><code class="text-accent-primary">#${order.id}</code></td>
            <td>
                <div class="font-medium text-primary">${order.user?.username ? '@' + order.user.username : 'ID: ' + order.user_id}</div>
                <div class="text-xs text-secondary">${order.user?.first_name || ''}</div>
            </td>
            <td>
                <div class="font-medium text-primary">${order.bot_type_name}</div>
            </td>
            <td class="text-right">
                <div class="font-medium text-primary">$${order.total_price_usd.toFixed(2)}</div>
                <div class="text-xs text-secondary">⭐ ${order.total_price_stars} Stars</div>
            </td>
            <td class="text-center">
                <span class="badge ${statusColors[order.status] || 'badge-primary'}">
                    ${statusTexts[order.status] || order.status}
                </span>
            </td>
            <td>
                <div class="text-sm text-secondary">${date}</div>
            </td>
            <td class="text-right">
                <div class="flex gap-2 justify-end">
                    <button onclick="viewOrder(${order.id})" class="btn btn-ghost btn-sm">👁️</button>
                    <button onclick="changeStatus(${order.id}, '${order.status}')" class="btn btn-ghost btn-sm">✏️</button>
                </div>
            </td>
        </tr>
        `;
    }).join('');
}

async function viewOrder(orderId) {
    try {
        const response = await fetch(`/api/custom-orders/${orderId}`);
        const order = await response.json();
        
        document.getElementById('orderDetailId').textContent = order.id;
        
        const featuresList = order.features.map(f => 
            `<li class="flex justify-between py-2 border-b" style="border-color: var(--color-border);">
                <span class="text-primary">${f.name_ru}</span>
                <span class="text-accent-primary">$${f.price_usd.toFixed(2)}</span>
            </li>`
        ).join('');
        
        const statusColors = {
            'pending': 'badge-warning',
            'paid': 'badge-success',
            'in_progress': 'badge-info',
            'completed': 'badge-primary',
            'cancelled': 'badge-error'
        };
        
        document.getElementById('orderDetailContent').innerHTML = `
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <div class="text-sm text-secondary mb-1">Пользователь</div>
                    <div class="font-medium text-primary">${order.user.username ? '@' + order.user.username : 'ID: ' + order.user.telegram_id}</div>
                    <div class="text-sm text-secondary">${order.user.first_name || ''}</div>
                </div>
                <div>
                    <div class="text-sm text-secondary mb-1">Статус</div>
                    <span class="badge ${statusColors[order.status] || 'badge-primary'}">
                        ${order.status}
                    </span>
                </div>
                <div>
                    <div class="text-sm text-secondary mb-1">Тип бота</div>
                    <div class="font-medium text-primary">${order.bot_type.name_ru}</div>
                </div>
                <div>
                    <div class="text-sm text-secondary mb-1">Дата создания</div>
                    <div class="text-primary">${Utils.formatDateTime(order.created_at)}</div>
                </div>
            </div>
            
            <div>
                <div class="text-sm text-secondary mb-2">Выбранные функции</div>
                <ul class="space-y-1">
                    ${featuresList || '<li class="text-secondary">Функции не выбраны</li>'}
                </ul>
            </div>
            
            <div>
                <div class="text-sm text-secondary mb-2">Описание</div>
                <div class="card">
                    ${formatOrderDescription(order.description || 'Нет описания', order.id)}
                </div>
            </div>
            
            <div>
                <div class="text-sm text-secondary mb-2">Контактная информация</div>
                <div class="card">${order.contact_info || 'Не указана'}</div>
            </div>
            
            <div class="grid grid-cols-3 gap-4 pt-4 border-t" style="border-color: var(--color-border);">
                <div>
                    <div class="text-sm text-secondary mb-1">Базовая цена</div>
                    <div class="font-medium text-primary">$${order.base_price_usd.toFixed(2)}</div>
                </div>
                <div>
                    <div class="text-sm text-secondary mb-1">Цена функций</div>
                    <div class="font-medium text-primary">$${order.features_price_usd.toFixed(2)}</div>
                </div>
                <div>
                    <div class="text-sm text-secondary mb-1">Общая стоимость</div>
                    <div class="font-bold text-lg text-accent-primary">$${order.total_price_usd.toFixed(2)}</div>
                    <div class="text-sm text-secondary">⭐ ${order.total_price_stars} Stars</div>
                </div>
            </div>
            
            ${order.admin_comment ? `
            <div>
                <div class="text-sm text-secondary mb-2">Комментарий администратора</div>
                <div class="card" style="background: var(--color-warning-bg); border-color: var(--color-warning);">
                    ${Utils.escapeHtml(order.admin_comment)}
                </div>
            </div>
            ` : ''}
        `;
        
        Modal.open('orderDetailModal');
    } catch (error) {
        console.error('Ошибка загрузки заказа:', error);
        Notification.show('Ошибка загрузки заказа', 'error');
    }
}

function changeStatus(orderId, currentStatus) {
    document.getElementById('statusOrderId').value = orderId;
    document.getElementById('statusSelect').value = currentStatus;
    document.getElementById('statusComment').value = '';
    document.getElementById('archiveFile').value = '';
    
    const statusSelect = document.getElementById('statusSelect');
    const archiveContainer = document.getElementById('archiveFileContainer');
    
    function toggleArchiveField() {
        if (statusSelect.value === 'completed') {
            archiveContainer.classList.remove('hidden');
        } else {
            archiveContainer.classList.add('hidden');
            document.getElementById('archiveFile').value = '';
        }
    }
    
    toggleArchiveField();
    statusSelect.addEventListener('change', toggleArchiveField);
    
    Modal.open('statusModal');
}

document.addEventListener('DOMContentLoaded', () => {
    const statusForm = document.getElementById('statusForm');
    if (statusForm) {
        statusForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const orderId = document.getElementById('statusOrderId').value;
            const status = document.getElementById('statusSelect').value;
            const comment = document.getElementById('statusComment').value;
            const archiveFile = document.getElementById('archiveFile').files[0];
            
            try {
                const formData = new FormData();
                formData.append('status', status);
                if (comment) formData.append('admin_comment', comment);
                
                if (status === 'completed' && archiveFile) {
                    formData.append('archive_file', archiveFile);
                }
                
                const response = await fetch(`/api/custom-orders/${orderId}/status`, {
                    method: 'PUT',
                    body: formData
                });
                
                if (response.ok) {
                    Modal.close('statusModal');
                    loadOrders(currentFilter);
                } else {
                    const errorData = await response.json();
                    Notification.show('Ошибка обновления статуса: ' + (errorData.detail || 'Неизвестная ошибка'), 'error');
                }
            } catch (error) {
                Notification.show('Ошибка обновления статуса', 'error');
            }
        });
    }

    loadOrders();
});

