/**
 * Logic for automatic registration flow
 */

const tg = window.Telegram.WebApp;

class RegistrationFlow {
    constructor(contestId, userId, username) {
        this.contestId = contestId;
        this.userId = userId;
        this.username = username;
        this.conditions = [];
        this.allMet = false;
        this.autoRegisterAttempted = false;

        this.elements = {
            container: document.getElementById('conditions-list'),
            loader: document.getElementById('initial-loader'),
            registrationForm: document.getElementById('registration-form'),
            successView: document.getElementById('success-view'),
            errorView: document.getElementById('error-view'),
            errorMessage: document.getElementById('error-message'),
            registerBtn: document.getElementById('register-btn'),
            regNum: document.getElementById('registration-number')
        };
    }

    async init() {
        this.showLoader(true);
        await this.checkStatus();
    }

    showLoader(show) {
        if (this.elements.loader) {
            this.elements.loader.style.display = show ? 'flex' : 'none';
        }
    }

    async checkStatus() {
        try {
            const response = await fetch(`/api/contests/${this.contestId}/auto-check?user_id=${this.userId}`, {
                headers: {
                    'X-Telegram-Init-Data': tg.initData
                }
            });

            if (!response.ok) throw new Error('Failed to fetch status');

            const data = await response.json();
            this.showLoader(false);

            if (data.status === 'already_registered') {
                this.showSuccess(data.participant);
                return;
            }

            this.conditions = data.conditions;
            this.allMet = data.all_met;
            this.renderConditions();

            if (this.allMet && !this.autoRegisterAttempted) {
                await this.register();
            }
        } catch (error) {
            console.error('Status check error:', error);
            this.showError('Ошибка при проверке статуса. Пожалуйста, попробуйте позже.');
        }
    }

    renderConditions() {
        if (!this.elements.container) return;

        this.elements.container.innerHTML = '';
        this.conditions.forEach(condition => {
            const item = document.createElement('div');
            item.className = 'condition-item' + (condition.met ? ' met' : '');

            let actionHtml = '';
            if (!condition.met) {
                if (condition.type === 'telegram') {
                    const url = condition.username ? `https://t.me/${condition.username}` : '#';
                    actionHtml = `<button class="btn btn-inline btn-sm" onclick="window.open('${url}', '_blank'); setTimeout(() => flow.checkStatus(), 3000)">Подписаться</button>`;
                } else if (condition.type === 'youtube') {
                    if (condition.connected) {
                        let url = '';
                        const yid = condition.id.trim();
                        if (yid.startsWith('http')) {
                            url = yid;
                        } else if (yid.includes('youtube.com')) {
                            url = yid.startsWith('//') ? `https:${yid}` : (yid.includes('://') ? yid : `https://${yid}`);
                        } else if (yid.startsWith('@')) {
                            url = `https://youtube.com/${yid}`;
                        } else if (yid.startsWith('UC') || yid.startsWith('HC')) {
                            url = `https://youtube.com/channel/${yid}`;
                        } else if (yid.length === 22 && /^[a-zA-Z0-9_-]+$/.test(yid)) {
                            // Looks like a channel ID without UC prefix
                            url = `https://youtube.com/channel/UC${yid}`;
                        } else {
                            url = `https://youtube.com/@${yid}`;
                        }
                        actionHtml = `<button class="btn btn-inline btn-sm" onclick="window.open('${url}', '_blank'); setTimeout(() => flow.checkStatus(), 3000)">Подписаться</button>`;
                    } else {
                        actionHtml = `<button class="btn btn-inline btn-sm btn-youtube" onclick="connectYouTube()">Привязать</button>`;
                    }
                }
            } else {
                actionHtml = '<span class="status-check">✅</span>';
            }

            item.innerHTML = `
                <div class="condition-info">
                    <span class="condition-icon">${condition.type === 'telegram' ? '📢' : '📺'}</span>
                    <span class="condition-title">${condition.title}</span>
                </div>
                <div class="condition-action">
                    ${actionHtml}
                </div>
            `;
            this.elements.container.appendChild(item);
        });

        if (!this.allMet) {
            this.elements.registrationForm.style.display = 'block';
            this.elements.registerBtn.disabled = true;
            this.elements.registerBtn.textContent = 'Выполните условия для участия';
        }
    }

    async register() {
        this.autoRegisterAttempted = true;
        this.elements.registerBtn.disabled = true;
        this.elements.registerBtn.innerHTML = '<span class="spinner-sm"></span> Регистрация...';

        try {
            const response = await fetch(`/api/contests/${this.contestId}/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Telegram-Init-Data': tg.initData
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    username: this.username || ''
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.showSuccess(data);
                this.fireConfetti();
                if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
            } else {
                this.showError(data.detail || 'Ошибка регистрации');
                this.elements.registerBtn.disabled = false;
                this.elements.registerBtn.textContent = 'Попробовать снова';
            }
        } catch (error) {
            this.showError('Ошибка сети');
            this.elements.registerBtn.disabled = false;
        }
    }

    showSuccess(participant) {
        this.elements.registrationForm.style.display = 'none';
        this.elements.successView.style.display = 'block';
        if (this.elements.regNum) {
            this.elements.regNum.textContent = participant.registration_number;
        }
    }

    showError(msg) {
        this.elements.errorView.style.display = 'block';
        this.elements.errorMessage.textContent = msg;
    }

    fireConfetti() {
        if (window.confetti) {
            window.confetti({
                particleCount: 150,
                spread: 70,
                origin: { y: 0.6 },
                colors: ['#7c8bff', '#9f7aea', '#ffffff']
            });
        }
    }
}
