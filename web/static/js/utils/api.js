/**
 * Утилиты для работы с API
 */

/**
 * Базовый URL API
 */
const API_BASE = '/api';

/**
 * Выполнить запрос к API
 * @param {string} endpoint - Конечная точка API
 * @param {Object} options - Опции запроса
 * @param {Object} tg - Объект Telegram WebApp (для авторизации)
 * @returns {Promise<Response>} Ответ от сервера
 */
export async function apiRequest(endpoint, options = {}, tg = null) {
    const url = `${API_BASE}${endpoint}`;
    
    // Добавляем параметры авторизации если есть Telegram WebApp
    if (tg) {
        const initData = tg.initData;
        if (initData) {
            const separator = endpoint.includes('?') ? '&' : '?';
            const authParam = `${separator}_auth=${encodeURIComponent(initData)}`;
            const fullUrl = url + authParam;
            
            const response = await fetch(fullUrl, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
            });
            
            return response;
        }
    }
    
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });
    
    return response;
}

/**
 * Получить данные конкурса
 * @param {number} contestId - ID конкурса
 * @param {number} userId - ID пользователя (опционально)
 * @returns {Promise<Object>} Данные конкурса
 */
export async function getContest(contestId, userId = null) {
    let url = `/contests/${contestId}`;
    if (userId) {
        url += `?user_id=${userId}`;
    }
    const response = await apiRequest(url);
    if (!response.ok) {
        throw new Error('Конкурс не найден');
    }
    return await response.json();
}

/**
 * Проверить подписки на каналы
 * @param {number} contestId - ID конкурса
 * @param {number} userId - ID пользователя
 * @returns {Promise<Object>} Результат проверки подписок
 */
export async function checkSubscriptions(contestId, userId) {
    const response = await apiRequest(`/contests/${contestId}/check-subscription?user_id=${userId}`);
    if (!response.ok) {
        throw new Error('Ошибка проверки подписки');
    }
    return await response.json();
}

/**
 * Зарегистрироваться в конкурсе
 * @param {number} contestId - ID конкурса
 * @param {number} userId - ID пользователя
 * @param {string} username - Username пользователя
 * @param {Object} tg - Объект Telegram WebApp
 * @returns {Promise<Object>} Результат регистрации
 */
export async function registerForContest(contestId, userId, username, youtubeChannelId, youtubeToken, tg) {
    const response = await apiRequest(
        `/contests/${contestId}/register`,
        {
            method: 'POST',
            body: JSON.stringify({
                user_id: userId,
                username: username,
                youtube_channel_id: youtubeChannelId,
                youtube_token: youtubeToken,
            }),
        },
        tg
    );
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка регистрации');
    }
    
    return await response.json();
}

/**
 * Получить информацию о конкурсе (без проверки статуса, для страницы результатов)
 * @param {number} contestId - ID конкурса
 * @returns {Promise<Object>} Данные конкурса
 */
export async function getContestInfo(contestId) {
    const response = await apiRequest(`/contests/${contestId}/info`);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Конкурс не найден');
    }
    return await response.json();
}

/**
 * Получить победителей конкурса
 * @param {number} contestId - ID конкурса
 * @returns {Promise<Array>} Список победителей
 */
export async function getWinners(contestId) {
    const response = await apiRequest(`/contests/${contestId}/winners`);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Результаты не найдены');
    }
    return await response.json();
}

/**
 * Проверить регистрацию пользователя
 * @param {number} contestId - ID конкурса
 * @param {number} userId - ID пользователя
 * @returns {Promise<Object|null>} Данные участника или null
 */
export async function checkRegistration(contestId, userId) {
    const response = await apiRequest(`/contests/${contestId}/participants/${userId}`);
    if (response.ok) {
        return await response.json();
    }
    return null;
}
