/**
 * JavaScript для страницы типов ботов
 */

let types = [];

async function loadTypes() {
    try {
        const response = await fetch('/api/bot-types');
        const data = await response.json();
        types = data.types;
        renderTypes();
    } catch (error) {
        console.error('Ошибка загрузки типов:', error);
        Notification.show('Ошибка загрузки типов', 'error');
    }
}

function renderTypes() {
    const tbody = document.getElementById('typesTableBody');
    if (!tbody) return;
    
    if (types.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-secondary">Нет типов ботов</td></tr>';
        return;
    }
    
    tbody.innerHTML = types.map(type => `
        <tr>
            <td><code class="text-accent-primary">${type.code}</code></td>
            <td>
                <div class="font-medium text-primary">${type.name_ru}</div>
                <div class="text-xs text-secondary">${type.name_en}</div>
            </td>
            <td class="text-right">
                <span class="font-medium text-primary">$${type.base_price_usd.toFixed(2)}</span>
            </td>
            <td class="text-center">
                <span class="text-secondary">${type.display_order}</span>
            </td>
            <td class="text-center">
                <span class="badge ${type.is_active ? 'badge-success' : 'badge-error'}">
                    ${type.is_active ? 'Активен' : 'Неактивен'}
                </span>
            </td>
            <td class="text-right">
                <div class="flex gap-2 justify-end">
                    <button onclick="editType(${type.id})" class="btn btn-ghost btn-sm">✏️</button>
                    <button onclick="deleteType(${type.id})" class="btn btn-ghost btn-sm text-error">🗑️</button>
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
            
            try {
                const response = await fetch('/api/bot-types', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams(data)
                });
                
                if (response.ok) {
                    closeModal('createModal');
                    e.target.reset();
                    loadTypes();
                } else {
                    Notification.show('Ошибка создания типа', 'error');
                }
            } catch (error) {
                Notification.show('Ошибка создания типа', 'error');
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
            delete data.id;
            
            try {
                const response = await fetch(`/api/bot-types/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams(data)
                });
                
                if (response.ok) {
                    closeModal('editModal');
                    loadTypes();
                } else {
                    Notification.show('Ошибка обновления типа', 'error');
                }
            } catch (error) {
                Notification.show('Ошибка обновления типа', 'error');
            }
        });
    }

    loadTypes();
});

async function editType(id) {
    const type = types.find(t => t.id === id);
    if (!type) return;
    
    document.getElementById('editId').value = type.id;
    document.getElementById('editCode').value = type.code;
    document.getElementById('editNameUk').value = type.name_uk;
    document.getElementById('editNameEn').value = type.name_en;
    document.getElementById('editNameRu').value = type.name_ru;
    document.getElementById('editDescUk').value = type.description_uk;
    document.getElementById('editDescEn').value = type.description_en;
    document.getElementById('editDescRu').value = type.description_ru;
    document.getElementById('editBasePrice').value = type.base_price_usd;
    document.getElementById('editDisplayOrder').value = type.display_order;
    document.getElementById('editIsActive').checked = type.is_active;
    
    openModal('editModal');
}

async function deleteType(id) {
    Confirm.action('Удалить этот тип бота?', async () => {
        try {
            const response = await fetch(`/api/bot-types/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadTypes();
            } else {
                Notification.show('Ошибка удаления типа', 'error');
            }
        } catch (error) {
            Notification.show('Ошибка удаления типа', 'error');
        }
    });
}

