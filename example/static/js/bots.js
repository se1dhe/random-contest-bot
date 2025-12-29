/**
 * JavaScript для страницы ботов
 */

let currentRate = 41.5;
let currentBotId = null;

// Загружаем курс валют при загрузке страницы
async function loadCurrencyRate() {
    try {
        const response = await fetch('/api/currency-rate');
        const data = await response.json();
        currentRate = data.rate;
        const rateElement = document.getElementById('currentRate');
        if (rateElement) {
            rateElement.textContent = `1 USD = ${currentRate.toFixed(2)} UAH`;
        }
    } catch (e) {
        const rateElement = document.getElementById('currentRate');
        if (rateElement) {
            rateElement.textContent = `1 USD ≈ ${currentRate} UAH (оффлайн)`;
        }
    }
}

async function refreshRate() {
    const rateElement = document.getElementById('currentRate');
    if (rateElement) {
        rateElement.textContent = 'Обновление...';
    }
    await loadCurrencyRate();
}

// Конвертация цены при вводе
document.addEventListener('DOMContentLoaded', () => {
    const priceUsdInput = document.getElementById('priceUsd');
    if (priceUsdInput) {
        priceUsdInput.addEventListener('input', (e) => {
            const usd = parseFloat(e.target.value) || 0;
            const uah = Math.ceil(usd * currentRate / 10) * 10;
            const stars = Math.max(5, Math.ceil(usd / 0.014 / 5) * 5);
            
            const uahPreview = document.getElementById('priceUahPreview');
            const starsPreview = document.getElementById('priceStarsPreview');
            const uahField = document.getElementById('priceUahField');
            const starsField = document.getElementById('priceStarsField');
            
            if (uahPreview) uahPreview.textContent = uah;
            if (starsPreview) starsPreview.textContent = stars;
            if (uahField) uahField.value = uah;
            if (starsField) starsField.value = stars;
        });
    }

    // Автоперевод
    let translateTimeout;
    const nameRuInput = document.getElementById('nameRu');
    const descRuInput = document.getElementById('descRu');
    
    if (nameRuInput) {
        nameRuInput.addEventListener('input', (e) => {
            clearTimeout(translateTimeout);
            translateTimeout = setTimeout(() => translateText(e.target.value, 'nameUk', 'nameEn'), 500);
        });
    }
    
    if (descRuInput) {
        descRuInput.addEventListener('input', (e) => {
            clearTimeout(translateTimeout);
            translateTimeout = setTimeout(() => translateText(e.target.value, 'descUk', 'descEn'), 800);
        });
    }

    // Создание бота
    const createForm = document.getElementById('createForm');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/bots', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    location.reload();
                } else {
                    Notification.show('Ошибка создания бота', 'error');
                }
            } catch (e) {
                Notification.show('Ошибка создания бота', 'error');
            }
        });
    }

    // Редактирование бота
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            data.is_active = document.getElementById('editIsActive').checked;
            
            try {
                const response = await fetch(`/api/bots/${data.bot_id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (response.ok) {
                    location.reload();
                } else {
                    Notification.show('Ошибка сохранения', 'error');
                }
            } catch (e) {
                Notification.show('Ошибка сохранения', 'error');
            }
        });
    }

    // Добавление версии
    const addVersionForm = document.getElementById('addVersionForm');
    if (addVersionForm) {
        addVersionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/bots/versions', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    Modal.close('addVersionModal');
                    openVersionsModal(currentBotId);
                } else {
                    Notification.show('Ошибка загрузки версии', 'error');
                }
            } catch (e) {
                Notification.show('Ошибка загрузки версии', 'error');
            }
        });
    }

    loadCurrencyRate();
});

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

// Редактирование бота
async function openEditModal(botId) {
    currentBotId = botId;
    try {
        const response = await fetch(`/api/bots/${botId}`);
        const bot = await response.json();
        
        document.getElementById('editBotId').value = bot.id;
        document.getElementById('editCategoryId').value = bot.category_id;
        document.getElementById('editPriceUsd').value = bot.price_usd;
        document.getElementById('editNameRu').value = bot.name_ru || '';
        document.getElementById('editNameUk').value = bot.name_uk || '';
        document.getElementById('editNameEn').value = bot.name_en || '';
        document.getElementById('editDescRu').value = bot.short_description_ru || '';
        document.getElementById('editDescUk').value = bot.short_description_uk || '';
        document.getElementById('editDescEn').value = bot.short_description_en || '';
        document.getElementById('editDiscount').value = bot.discount_percent || 0;
        document.getElementById('editIsActive').checked = bot.is_active;
        
        Modal.open('editModal');
    } catch (e) {
        Notification.show('Ошибка загрузки данных бота', 'error');
    }
}

// Версии бота
async function openVersionsModal(botId) {
    currentBotId = botId;
    document.getElementById('versionBotId').value = botId;
    Modal.open('versionsModal');
    
    try {
        const response = await fetch(`/api/bots/${botId}/versions`);
        const data = await response.json();
        
        const container = document.getElementById('versionsList');
        if (data.versions && data.versions.length > 0) {
            container.innerHTML = data.versions.map(v => `
                <div class="card">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-bold text-primary">v${v.version_number}</span>
                        <span class="text-xs text-secondary">${new Date(v.created_at).toLocaleDateString()}</span>
                    </div>
                    <p class="text-sm text-secondary">${v.changelog_ru || 'Нет описания'}</p>
                    <div class="flex items-center justify-between mt-2 text-xs">
                        <span class="text-secondary">Размер: ${(v.file_size / 1024 / 1024).toFixed(2)} MB</span>
                        ${v.update_price_usd > 0 ? `<span class="text-warning">$${v.update_price_usd}</span>` : '<span class="text-success">Бесплатно</span>'}
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="text-secondary text-center py-4">Нет версий</p>';
        }
    } catch (e) {
        document.getElementById('versionsList').innerHTML = '<p class="text-error text-center py-4">Ошибка загрузки</p>';
    }
}

function openAddVersionModal() {
    document.getElementById('versionBotId').value = currentBotId;
    Modal.open('addVersionModal');
}

// Удаление бота
function confirmDelete(botId, botName) {
    Confirm.action(`Удалить бота "${botName}"? Это действие нельзя отменить.`, () => {
        deleteBot(botId);
    });
}

async function deleteBot(botId) {
    try {
        const response = await fetch(`/api/bots/${botId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            location.reload();
        } else {
            Notification.show('Ошибка удаления', 'error');
        }
    } catch (e) {
        Notification.show('Ошибка удаления', 'error');
    }
}

