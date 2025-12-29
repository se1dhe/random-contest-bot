/**
 * Общие утилиты и функции для админ-панели
 */

// ===== МОДАЛЬНЫЕ ОКНА =====
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Закрытие модалок по клику вне их
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });
    
    // Закрытие по Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(modal => {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            });
        }
    });
});

// ===== УТИЛИТЫ =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// ===== API ЗАПРОСЫ =====
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Ошибка запроса' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ===== УВЕДОМЛЕНИЯ =====
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    const styles = {
        position: 'fixed',
        top: '1rem',
        right: '1rem',
        padding: '1rem 1.5rem',
        borderRadius: '0.75rem',
        color: 'white',
        fontWeight: '600',
        zIndex: '9999',
        animation: 'fadeIn 0.3s ease-out',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)'
    };
    
    const colors = {
        success: { background: '#10b981' },
        error: { background: '#ef4444' },
        warning: { background: '#f59e0b' },
        info: { background: '#3b82f6' }
    };
    
    Object.assign(notification.style, styles, colors[type] || colors.info);
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateY(-20px)';
        notification.style.transition = 'all 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ===== ПОДТВЕРЖДЕНИЕ =====
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ===== ФОРМАТИРОВАНИЕ =====
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ===== ДЕБАУНС =====
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== МОБИЛЬНОЕ МЕНЮ =====
function toggleMobileMenu() {
    const sidebar = document.getElementById('sidebar');
    const btn = document.getElementById('mobileMenuBtn');
    const overlay = document.getElementById('mobileMenuOverlay');
    
    if (sidebar && btn && overlay) {
        const isOpen = sidebar.classList.contains('open');
        
        if (isOpen) {
            sidebar.classList.remove('open');
            btn.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        } else {
            sidebar.classList.add('open');
            btn.classList.add('active');
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }
}

// Закрытие мобильного меню при клике на ссылку
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    toggleMobileMenu();
                }
            });
        });
    }
    
    // Закрытие при изменении размера окна
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth > 768) {
                const sidebar = document.getElementById('sidebar');
                const btn = document.getElementById('mobileMenuBtn');
                const overlay = document.getElementById('mobileMenuOverlay');
                
                if (sidebar && btn && overlay) {
                    sidebar.classList.remove('open');
                    btn.classList.remove('active');
                    overlay.classList.remove('active');
                    document.body.style.overflow = '';
                }
            }
        }, 250);
    });
});

// ===== ЭКСПОРТ =====
window.Modal = { open: openModal, close: closeModal };
window.Utils = {
    escapeHtml,
    formatDate,
    formatDateTime,
    formatCurrency,
    formatFileSize,
    debounce
};
window.API = { request: apiRequest };
window.Notification = { show: showNotification };
window.Confirm = { action: confirmAction };
window.toggleMobileMenu = toggleMobileMenu;

