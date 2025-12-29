/**
 * JavaScript для страницы промокодов
 */

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
            const data = {};
            
            formData.forEach((value, key) => {
                if (value) {
                    if (key === 'discount_percent' || key === 'max_uses' || key === 'bot_product_id') {
                        data[key] = parseInt(value) || null;
                    } else {
                        data[key] = value;
                    }
                }
            });
            
            try {
                const response = await fetch('/api/promos', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    location.reload();
                } else {
                    Notification.show('Ошибка создания промокода', 'error');
                }
            } catch (error) {
                Notification.show('Ошибка создания промокода', 'error');
            }
        });
    }
});

async function deletePromo(id) {
    Confirm.action('Удалить промокод?', async () => {
        try {
            const response = await fetch(`/api/promos/${id}`, {method: 'DELETE'});
            
            if (response.ok) {
                location.reload();
            } else {
                Notification.show('Ошибка удаления', 'error');
            }
        } catch (error) {
            Notification.show('Ошибка удаления', 'error');
        }
    });
}

