/**
 * JavaScript для страницы категорий
 */

function openModal(id) {
    Modal.open(id);
}

function closeModal(id) {
    Modal.close(id);
}

async function translateText(text, ukField, enField) {
    if (!text.trim()) return;
    try {
        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, source_lang: 'ru' })
        });
        const data = await response.json();
        if (data.translations) {
            const ukElement = document.getElementById(ukField);
            const enElement = document.getElementById(enField);
            if (ukElement) ukElement.value = data.translations.uk || text;
            if (enElement) enElement.value = data.translations.en || text;
        }
    } catch (e) {
        console.error('Ошибка перевода:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Автоперевод названия категории
    let translateTimeout;
    const nameRuInput = document.getElementById('nameRu');
    
    if (nameRuInput) {
        nameRuInput.addEventListener('input', (e) => {
            clearTimeout(translateTimeout);
            translateTimeout = setTimeout(() => translateText(e.target.value, 'nameUk', 'nameEn'), 500);
        });
    }

    const createForm = document.getElementById('createForm');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/categories', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    location.reload();
                } else {
                    Notification.show('Ошибка создания категории', 'error');
                }
            } catch (error) {
                Notification.show('Ошибка создания категории', 'error');
            }
        });
    }
});

