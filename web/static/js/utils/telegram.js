/**
 * Утилиты для работы с Telegram WebApp
 */

/**
 * Инициализация Telegram WebApp
 * @returns {Object} Объект Telegram WebApp
 */
export function initTelegramWebApp() {
    if (typeof Telegram === 'undefined' || !Telegram.WebApp) {
        throw new Error('Telegram WebApp API не доступен');
    }
    
    const tg = Telegram.WebApp;
    tg.ready();
    tg.expand();
    
    return tg;
}

/**
 * Получить данные пользователя из initData
 * @param {Object} tg - Объект Telegram WebApp
 * @returns {Object|null} Данные пользователя
 */
export function getUserData(tg) {
    return tg?.initDataUnsafe?.user || null;
}

/**
 * Получить initData для передачи в API
 * @param {Object} tg - Объект Telegram WebApp
 * @returns {string} initData строка
 */
export function getInitData(tg) {
    return tg?.initData || '';
}

/**
 * Получить параметры авторизации для API запросов
 * @param {Object} tg - Объект Telegram WebApp
 * @returns {string} Строка с параметрами авторизации
 */
export function getAuthParams(tg) {
    const initData = getInitData(tg);
    if (!initData) {
        return '';
    }
    return `&_auth=${encodeURIComponent(initData)}`;
}
