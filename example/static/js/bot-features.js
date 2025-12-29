/**
 * JavaScript для страницы функций ботов
 */

let features = [];

async function loadFeatures() {
    try {
        const response = await fetch('/api/bot-features');
        const data = await response.json();
        features = data.features;
        renderFeatures();
    } catch (error) {
        console.error('Ошибка загрузки функций:', error);
        Notification.show('Ошибка загрузки функций', 'error');
    }
}

function renderFeatures() {
    const tbody = document.getElementById('featuresTableBody');
    if (!tbody) return;
    
    if (features.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-secondary">Нет функций</td></tr>';
        return;
    }
    
    tbody.innerHTML = features.map(feature => `
        <tr>
            <td>
                <div class="font-medium text-primary">${feature.name_ru}</div>
                <div class="text-xs text-secondary">${feature.name_en}</div>
            </td>
            <td>
                <span class="text-secondary">${feature.bot_type_id ? 'Специфичная' : 'Универсальная'}</span>
            </td>
            <td class="text-right">
                <span class="font-medium text-primary">$${feature.price_usd.toFixed(2)}</span>
            </td>
            <td class="text-center">
                <span class="text-secondary">${feature.display_order}</span>
            </td>
            <td class="text-center">
                <span class="badge ${feature.is_active ? 'badge-success' : 'badge-error'}">
                    ${feature.is_active ? 'Активна' : 'Неактивна'}
                </span>
            </td>
            <td class="text-right">
                <div class="flex gap-2 justify-end">
                    <button onclick="editFeature(${feature.id})" class="btn btn-ghost btn-sm">✏️</button>
                    <button onclick="deleteFeature(${feature.id})" class="btn btn-ghost btn-sm text-error">🗑️</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function openModal(id) {
    Modal.open(id);
}

function closeModal(id) {
    Modal.close(id);
}

document.addEventListener('DOMContentLoaded', () => {
    const createForm = document.getElementById('createForm');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.is_active = formData.has('is_active');
            if (!data.bot_type_id) data.bot_type_id = null;
            
            try {
                const response = await fetch('/api/bot-features', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams(data)
                });
                
                if (response.ok) {
                    closeModal('createModal');
                    e.target.reset();
                    loadFeatures();
                } else {
                    Notification.show('Ошибка создания функции', 'error');
                }
            } catch (error) {
                Notification.show('Ошибка создания функции', 'error');
            }
        });
    }

    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const id = formData.get('id');
            const data = Object.fromEntries(formData);
            data.is_active = formData.has('is_active');
            if (!data.bot_type_id) data.bot_type_id = null;
            delete data.id;
            
            try {
                const response = await fetch(`/api/bot-features/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams(data)
                });
                
                if (response.ok) {
                    closeModal('editModal');
                    loadFeatures();
                } else {
                    Notification.show('Ошибка обновления функции', 'error');
                }
            } catch (error) {
                Notification.show('Ошибка обновления функции', 'error');
            }
        });
    }

    loadFeatures();
});

async function editFeature(id) {
    const feature = features.find(f => f.id === id);
    if (!feature) return;
    
    document.getElementById('editId').value = feature.id;
    document.getElementById('editNameUk').value = feature.name_uk;
    document.getElementById('editNameEn').value = feature.name_en;
    document.getElementById('editNameRu').value = feature.name_ru;
    document.getElementById('editDescUk').value = feature.description_uk;
    document.getElementById('editDescEn').value = feature.description_en;
    document.getElementById('editDescRu').value = feature.description_ru;
    document.getElementById('editPrice').value = feature.price_usd;
    document.getElementById('editBotTypeId').value = feature.bot_type_id || '';
    document.getElementById('editDisplayOrder').value = feature.display_order;
    document.getElementById('editIsActive').checked = feature.is_active;
    
    openModal('editModal');
}

async function deleteFeature(id) {
    Confirm.action('Удалить эту функцию?', async () => {
        try {
            const response = await fetch(`/api/bot-features/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadFeatures();
            } else {
                Notification.show('Ошибка удаления функции', 'error');
            }
        } catch (error) {
            Notification.show('Ошибка удаления функции', 'error');
        }
    });
}

