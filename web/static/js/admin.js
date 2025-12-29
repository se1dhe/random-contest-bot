/**
 * Vue.js компонент для админ-панели
 */

import { initTelegramWebApp, getUserData, getAuthParams } from './utils/telegram.js';
import { apiRequest } from './utils/api.js';

console.log('Загрузка admin.js...');

if (typeof Vue === 'undefined') {
    console.error('Vue не загружен!');
    document.getElementById('app').innerHTML = `
        <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: #0a0a0f; color: #fff; font-family: 'Inter', Arial, sans-serif;">
            <div style="text-align: center; padding: 2rem; background: rgba(26, 26, 36, 0.9); border-radius: 1rem; border: 1px solid rgba(255, 255, 255, 0.1);">
                <h1 style="font-size: 2rem; margin-bottom: 1rem;">❌ Ошибка загрузки</h1>
                <p>Vue.js не загружен. Проверьте подключение к интернету.</p>
            </div>
        </div>
    `;
    throw new Error('Vue не загружен');
}

const { createApp } = Vue;

let tg = null;
let userData = null;
let ADMIN_ID = null;

try {
    tg = initTelegramWebApp();
    userData = getUserData(tg);
    ADMIN_ID = userData?.id || null;
    console.log('Telegram WebApp инициализирован, adminId:', ADMIN_ID);
} catch (error) {
    console.error('Ошибка инициализации Telegram WebApp:', error);
    // Если открыто в обычном браузере, показываем сообщение
    const app = document.getElementById('app');
    if (app) {
        app.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: #0a0a0f; color: #fff; font-family: 'Inter', Arial, sans-serif;">
                <div style="text-align: center; padding: 2rem; background: rgba(26, 26, 36, 0.9); border-radius: 1rem; border: 1px solid rgba(255, 255, 255, 0.1);">
                    <h1 style="font-size: 2rem; margin-bottom: 1rem;">🔒 Доступ запрещен</h1>
                    <p style="margin-bottom: 0.5rem;">Эта страница доступна только через Telegram WebApp.</p>
                    <p style="margin-bottom: 1rem;">Используйте команду <code style="background: rgba(255, 255, 255, 0.1); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">/admin</code> в боте.</p>
                    <p style="color: #888; font-size: 0.9rem;">Ошибка: ${error.message}</p>
                </div>
            </div>
        `;
    }
    // Не выбрасываем ошибку, чтобы не ломать консоль
}

console.log('Создание Vue приложения...');

const app = createApp({
    data() {
        return {
            adminId: ADMIN_ID,
            activeTab: 'contests',
            channels: [],
            contests: [],
            loading: {
                channels: false,
                contests: false,
                stats: false
            },
            contestForm: {
                title: '',
                description: '',
                channelId: null,
                endDate: '',
                drawMethod: 'random',
                prizeCount: 3,
                prizes: [],
                sponsors: [],
                requireYoutubeSubscription: false,
                youtubeSubscriptionDaysRequired: 0
            },
            channelForm: {
                username: '',
                channelId: '',
                channelTitle: '',
                youtubeChannelId: '',
                resolving: false
            },
            selectedContestForStats: null,
            stats: null,
            showAddChannelModal: false,
            showEditChannelModal: false,
            editingChannel: null
        };
    },
    
    async mounted() {
        console.log('Admin app mounted, adminId:', this.adminId);
        
        if (!this.adminId) {
            alert('Ошибка: не удалось определить пользователя');
            return;
        }
        
        try {
            // Анимация появления контейнера
            if (typeof gsap !== 'undefined') {
                this.$nextTick(() => {
                    const container = document.querySelector('.admin-container');
                    if (container) {
                        gsap.from(container, {
                            opacity: 0,
                            y: 20,
                            duration: 0.6,
                            ease: 'power3.out'
                        });
                    }
                });
            }
            
            await Promise.all([
                this.loadChannels(),
                this.loadContests()
            ]);
            
            this.updatePrizeInputs();
            
            // Анимации для плавного появления
            this.$nextTick(() => {
                this.animateContent();
            });
        } catch (error) {
            console.error('Ошибка при инициализации админки:', error);
            alert('Ошибка при загрузке админ-панели: ' + error.message);
        }
    },
    
    methods: {
        async loadChannels() {
            try {
                this.loading.channels = true;
                const response = await apiRequest(`/admin/channels?user_id=${this.adminId}`, {}, tg);
                if (!response.ok) throw new Error('Ошибка загрузки каналов');
                this.channels = await response.json();
            } catch (error) {
                console.error('Ошибка загрузки каналов:', error);
                alert(`Ошибка загрузки каналов: ${error.message}`);
            } finally {
                this.loading.channels = false;
            }
        },
        
        async loadContests() {
            try {
                this.loading.contests = true;
                const response = await apiRequest(`/admin/contests?user_id=${this.adminId}`, {}, tg);
                if (!response.ok) throw new Error('Ошибка загрузки конкурсов');
                const allContests = await response.json();
                // Фильтруем завершенные и опубликованные конкурсы
                this.contests = allContests.filter(contest => 
                    contest.status !== 'finished' && contest.status !== 'results_published'
                );
            } catch (error) {
                console.error('Ошибка загрузки конкурсов:', error);
                alert(`Ошибка загрузки конкурсов: ${error.message}`);
            } finally {
                this.loading.contests = false;
            }
        },
        
        animateContent() {
            const cards = document.querySelectorAll('.content-card, .card');
            
            if (typeof anime !== 'undefined') {
                // Используем Anime.js для более плавных анимаций
                anime({
                    targets: cards,
                    opacity: [0, 1],
                    translateY: [25, 0],
                    scale: [0.96, 1],
                    delay: anime.stagger(80),
                    duration: 700,
                    easing: 'easeOutElastic(1, .7)'
                });
            } else if (typeof gsap !== 'undefined') {
                // Fallback на GSAP
                cards.forEach((card, index) => {
                    gsap.fromTo(card, {
                        opacity: 0,
                        y: 25,
                        scale: 0.96
                    }, {
                        opacity: 1,
                        y: 0,
                        scale: 1,
                        duration: 0.5,
                        delay: index * 0.08,
                        ease: 'power3.out'
                    });
                });
            }
        },
        
        switchTab(tabName) {
            // Плавный переход между вкладками
            if (this.activeTab === tabName) return;
            
            this.activeTab = tabName;
            
            // Вибрация при переключении
            if (tg && tg.HapticFeedback) {
                tg.HapticFeedback.impactOccurred('light');
            }
            
            if (tabName === 'create') {
                this.loadChannelsForSelect();
            } else if (tabName === 'stats') {
                this.loadStats();
            }
        },
        
        loadChannelsForSelect() {
            // Каналы уже загружены
        },
        
        async resolveChannelUsername() {
            const username = this.channelForm.username.trim();
            
            if (!username) {
                this.channelForm.channelId = '';
                this.channelForm.channelTitle = '';
                return;
            }
            
            const numericId = parseInt(username);
            if (!isNaN(numericId) && numericId < 0) {
                this.channelForm.channelId = numericId;
                this.channelForm.channelTitle = '';
                return;
            }
            
            this.channelForm.resolving = true;
            
            try {
                const cleanUsername = username.replace(/^@/, '');
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/admin/channels/resolve-username?username=${encodeURIComponent(cleanUsername)}&user_id=${this.adminId}${authParams}`
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Канал не найден');
                }
                
                const channelInfo = await response.json();
                this.channelForm.channelId = channelInfo.channel_id;
                this.channelForm.channelTitle = channelInfo.channel_title;
                
                if (channelInfo.channel_username && channelInfo.channel_username !== cleanUsername) {
                    this.channelForm.username = channelInfo.channel_username;
                }
            } catch (error) {
                this.channelForm.channelId = '';
                this.channelForm.channelTitle = '';
                alert(`Ошибка: ${error.message}`);
            } finally {
                this.channelForm.resolving = false;
            }
        },
        
        async addChannel() {
            if (!this.channelForm.channelId || !this.channelForm.channelTitle) {
                alert('Пожалуйста, заполните username канала для автоматического получения ID и названия');
                return;
            }
            
            try {
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/admin/channels?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            channel_id: parseInt(this.channelForm.channelId),
                            channel_title: this.channelForm.channelTitle,
                            channel_username: this.channelForm.username || null,
                            youtube_channel_id: this.channelForm.youtubeChannelId || null
                        })
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка добавления канала');
                }
                
                alert('Канал успешно добавлен');
                this.channelForm = {
                    username: '',
                    channelId: '',
                    channelTitle: '',
                    youtubeChannelId: '',
                    resolving: false
                };
                this.showAddChannelModal = false;
                await this.loadChannels();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        openAddChannelModal() {
            this.showAddChannelModal = true;
        },
        
        closeAddChannelModal() {
            this.showAddChannelModal = false;
            this.channelForm = {
                username: '',
                channelId: '',
                channelTitle: '',
                youtubeChannelId: '',
                resolving: false
            };
        },
        
        async         editChannel(channel) {
            this.editingChannel = channel;
            this.channelForm = {
                username: channel.channel_username || '',
                channelId: channel.channel_id.toString(),
                channelTitle: channel.channel_title,
                youtubeChannelId: channel.youtube_channel_id || '',
                resolving: false
            };
            this.showEditChannelModal = true;
        },
        
        async updateChannel() {
            if (!this.channelForm.channelId || !this.channelForm.channelTitle) {
                alert('Пожалуйста, заполните все обязательные поля');
                return;
            }
            
            try {
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/admin/channels/${this.editingChannel.channel_id}?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            channel_id: parseInt(this.channelForm.channelId),
                            channel_title: this.channelForm.channelTitle,
                            channel_username: this.channelForm.username || null,
                            youtube_channel_id: this.channelForm.youtubeChannelId || null
                        })
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка обновления канала');
                }
                
                alert('Канал успешно обновлен');
                this.closeEditChannelModal();
                await this.loadChannels();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        closeEditChannelModal() {
            this.showEditChannelModal = false;
            this.editingChannel = null;
            this.channelForm = {
                username: '',
                channelId: '',
                channelTitle: '',
                youtubeChannelId: '',
                resolving: false
            };
        },
        
        async deleteChannel(channelId) {
            if (!confirm('Вы уверены, что хотите удалить этот канал?')) {
                return;
            }
            
            try {
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/admin/channels/${channelId}?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'DELETE'
                    }
                );
                
                if (!response.ok) {
                    throw new Error('Ошибка удаления канала');
                }
                
                alert('Канал успешно удален');
                await this.loadChannels();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        updatePrizeInputs() {
            const count = this.contestForm.prizeCount;
            this.contestForm.prizes = [];
            
            for (let i = 1; i <= count; i++) {
                this.contestForm.prizes.push({
                    place: i,
                    title: '',
                    description: ''
                });
            }
        },
        
        addSponsor() {
            this.contestForm.sponsors.push({
                channelId: '',
                channelTitle: ''
            });
        },
        
        removeSponsor(index) {
            this.contestForm.sponsors.splice(index, 1);
        },
        
        async createContest() {
            if (!this.contestForm.title || !this.contestForm.channelId || !this.contestForm.endDate) {
                alert('Заполните все обязательные поля');
                return;
            }
            
            if (this.contestForm.prizes.some(p => !p.title)) {
                alert('Заполните названия всех призовых мест');
                return;
            }
            
            try {
                // Правильно обрабатываем дату из datetime-local input
                // datetime-local возвращает дату в формате YYYY-MM-DDTHH:mm (локальное время)
                let endDateStr = this.contestForm.endDate;
                
                if (!endDateStr) {
                    throw new Error('Дата не указана');
                }
                
                // Если дата не содержит секунды, добавляем их
                if (endDateStr && endDateStr.split(':').length === 2) {
                    endDateStr += ':00';
                }
                
                // Создаем Date объект из локального времени
                // datetime-local возвращает дату в локальном времени, но без таймзоны
                const localDate = new Date(endDateStr);
                
                // Проверяем валидность даты
                if (isNaN(localDate.getTime())) {
                    throw new Error('Неверный формат даты. Убедитесь, что дата и время указаны правильно.');
                }
                
                // Конвертируем в ISO строку (UTC) - это добавит Z в конце
                const endDateISO = localDate.toISOString();
                
                const authParams = getAuthParams(tg);
                
                const response = await fetch(
                    `/api/admin/contests?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            title: this.contestForm.title,
                            description: this.contestForm.description || null,
                            channel_id: parseInt(this.contestForm.channelId),
                            end_date: endDateISO,
                            prize_count: this.contestForm.prizeCount,
                            draw_method: this.contestForm.drawMethod,
                            prizes: this.contestForm.prizes.map(p => ({
                                place: p.place,
                                title: p.title,
                                description: p.description || null
                            })),
                            sponsors: this.contestForm.sponsors.length > 0 
                                ? this.contestForm.sponsors.map(s => ({
                                    channel_id: parseInt(s.channelId),
                                    channel_title: s.channelTitle
                                }))
                                : null,
                            require_youtube_subscription: this.contestForm.requireYoutubeSubscription,
                            youtube_subscription_days_required: this.contestForm.requireYoutubeSubscription ? (this.contestForm.youtubeSubscriptionDaysRequired || 0) : 0
                        })
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка создания конкурса');
                }
                
                alert('Конкурс успешно создан!');
                
                this.contestForm = {
                    title: '',
                    description: '',
                    channelId: null,
                    endDate: '',
                    drawMethod: 'random',
                    prizeCount: 3,
                    prizes: [],
                    sponsors: [],
                    requireYoutubeSubscription: false,
                    youtubeSubscriptionDaysRequired: 0
                };
                this.updatePrizeInputs();
                
                await this.loadContests();
                this.switchTab('contests');
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        async publishContest(contestId) {
            if (!confirm('Опубликовать конкурс в канале?')) {
                return;
            }
            
            try {
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/publish/contest/${contestId}?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'POST'
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка публикации');
                }
                
                alert('Конкурс успешно опубликован!');
                await this.loadContests();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        async finishContest(contestId) {
            if (!confirm('Вы уверены, что хотите завершить конкурс и провести розыгрыш?')) {
                return;
            }
            
            try {
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/admin/contests/${contestId}/draw?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'POST'
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка проведения розыгрыша');
                }
                
                alert('Розыгрыш успешно проведен!');
                await this.loadContests();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        async publishResults(contestId) {
            if (!confirm('Опубликовать результаты конкурса в канале?')) {
                return;
            }
            
            try {
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/publish/results/${contestId}?user_id=${this.adminId}${authParams}`,
                    {
                        method: 'POST'
                    }
                );
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Ошибка публикации результатов');
                }
                
                alert('Результаты успешно опубликованы!');
                await this.loadContests();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            }
        },
        
        async loadStats() {
            if (!this.selectedContestForStats) {
                this.stats = null;
                return;
            }
            
            try {
                this.loading.stats = true;
                const authParams = getAuthParams(tg);
                const response = await fetch(
                    `/api/admin/contests/${this.selectedContestForStats}/stats?user_id=${this.adminId}${authParams}`
                );
                
                if (!response.ok) {
                    throw new Error('Ошибка загрузки статистики');
                }
                
                this.stats = await response.json();
            } catch (error) {
                alert(`Ошибка: ${error.message}`);
            } finally {
                this.loading.stats = false;
            }
        },
        
        getStatusClass(status) {
            return status.toLowerCase();
        },
        
        getStatusText(status) {
            const statusMap = {
                'DRAFT': 'Черновик',
                'ACTIVE': 'Активен',
                'FINISHED': 'Завершен',
                'RESULTS_PUBLISHED': 'Опубликован'
            };
            return statusMap[status] || status;
        },
        
        formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU', { 
                day: '2-digit', 
                month: '2-digit', 
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
    },
    
    template: `
        <div class="admin-container">
            <div class="admin-header">
                <div class="admin-header-title">
                    <span>⚙️</span>
                    <span>Админ-панель</span>
                </div>
            </div>
            
            <div class="admin-content">
                <!-- Секция конкурсов -->
                <transition name="slide">
                    <div v-if="activeTab === 'contests'" class="admin-section active" key="contests">
                    <h2 class="section-title">Конкурсы</h2>
                    <div v-if="loading.contests" class="loading">
                        <div class="spinner"></div>
                        <span>Загрузка...</span>
                    </div>
                    <div v-else-if="contests.length === 0" class="admin-card">
                        <p class="text-secondary text-center">Конкурсы не созданы</p>
                    </div>
                    <div v-else class="admin-list">
                        <div 
                            v-for="(contest, index) in contests" 
                            :key="contest.id" 
                            class="admin-list-item"
                            :style="{ animationDelay: (index * 0.05) + 's' }"
                        >
                            <div class="admin-list-item-header">
                                <div style="flex: 1; min-width: 0;">
                                    <div class="admin-list-item-title">{{ contest.title }}</div>
                                    <div class="admin-list-item-meta">
                                        <span>👥 {{ contest.participants_count || 0 }}</span>
                                        <span>📅 {{ new Date(contest.end_date).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) }}</span>
                                        <span>🕐 {{ new Date(contest.end_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) }}</span>
                                        <span v-if="contest.channel">📢 {{ contest.channel.channel_title || contest.channel.channel_username || 'Канал' }}</span>
                                    </div>
                                </div>
                                <span :class="['status-badge', getStatusClass(contest.status)]">
                                    {{ getStatusText(contest.status) }}
                                </span>
                            </div>
                            <div class="admin-list-item-actions">
                                <button 
                                    v-if="contest.status === 'draft'" 
                                    @click="publishContest(contest.id)" 
                                    class="btn btn-success btn-sm"
                                >
                                    Опубликовать
                                </button>
                                <button 
                                    v-if="contest.status === 'active'" 
                                    @click="finishContest(contest.id)" 
                                    class="btn btn-warning btn-sm"
                                >
                                    Завершить
                                </button>
                                <button 
                                    v-if="contest.status === 'finished'" 
                                    @click="publishResults(contest.id)" 
                                    class="btn btn-primary btn-sm"
                                >
                                    Опубликовать результаты
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                </transition>
                
                <!-- Секция каналов -->
                <transition name="slide">
                    <div v-if="activeTab === 'channels'" class="admin-section active" key="channels">
                    <div class="admin-section-header">
                        <h2 class="section-title">Каналы</h2>
                        <button @click="openAddChannelModal" class="btn btn-primary">
                            <span>➕</span>
                            <span>Добавить канал</span>
                        </button>
                    </div>
                    
                    <div v-if="loading.channels" class="loading">
                        <div class="spinner"></div>
                        <span>Загрузка...</span>
                    </div>
                    <div v-else-if="channels.length === 0" class="admin-card">
                        <div class="empty-state">
                            <div class="empty-state-icon">📢</div>
                            <h3 class="empty-state-title">Каналы не добавлены</h3>
                            <p class="empty-state-description">Добавьте первый канал для начала работы</p>
                        </div>
                    </div>
                    <div v-else class="channels-grid">
                        <div 
                            v-for="(channel, index) in channels" 
                            :key="channel.channel_id" 
                            class="channel-card"
                            :style="{ animationDelay: (index * 0.08) + 's' }"
                        >
                            <div class="channel-card-header">
                                <div class="channel-card-icon">📢</div>
                                <div class="channel-card-info">
                                    <h3 class="channel-card-title">{{ channel.channel_title }}</h3>
                                    <div class="channel-card-meta">
                                        <span v-if="channel.channel_username" class="channel-card-username">
                                            {{ channel.channel_username.startsWith('@') ? channel.channel_username : '@' + channel.channel_username }}
                                        </span>
                                        <span class="channel-card-id">ID: {{ channel.channel_id }}</span>
                                        <span v-if="channel.youtube_channel_id" class="channel-card-youtube" style="display: block; margin-top: 0.25rem; color: var(--text-secondary); font-size: 0.85rem;">
                                            📺 YouTube: {{ channel.youtube_channel_id }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div class="channel-card-actions">
                                <button @click="editChannel(channel)" class="btn btn-secondary btn-sm">
                                    Редактировать
                                </button>
                                <button @click="deleteChannel(channel.channel_id)" class="btn btn-error btn-sm">
                                    Удалить
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                </transition>
                
                <!-- Секция создания конкурса -->
                <transition name="slide">
                    <div v-if="activeTab === 'create'" class="admin-section active" key="create">
                    <h2 class="section-title">Создать конкурс</h2>
                    <div class="admin-card">
                        <form @submit.prevent="createContest" class="admin-form">
                            <div class="form-group">
                                <label class="form-label">Название конкурса</label>
                                <input type="text" class="form-input" v-model="contestForm.title" required>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Описание (опционально)</label>
                                <textarea class="form-textarea" v-model="contestForm.description"></textarea>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Канал</label>
                                <select class="form-select" v-model="contestForm.channelId" required>
                                    <option :value="null">Выберите канал...</option>
                                    <option v-for="channel in channels" :key="channel.channel_id" :value="channel.channel_id">
                                        {{ channel.channel_title }}
                                    </option>
                                </select>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label class="form-label">Дата окончания</label>
                                    <input type="datetime-local" class="form-input" v-model="contestForm.endDate" required>
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Метод розыгрыша</label>
                                    <select class="form-select" v-model="contestForm.drawMethod" required>
                                        <option value="random">Случайный выбор</option>
                                        <option value="by_activity">По активности</option>
                                    </select>
                                </div>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Количество призовых мест</label>
                                <input 
                                    type="number" 
                                    class="form-input" 
                                    v-model.number="contestForm.prizeCount"
                                    min="1" 
                                    max="10" 
                                    @change="updatePrizeInputs"
                                    required
                                >
                            </div>
                            <div class="form-group">
                                <label class="form-label">Призовые места</label>
                                <div 
                                    v-for="(prize, index) in contestForm.prizes" 
                                    :key="prize.place" 
                                    class="prize-item"
                                    :style="{ animationDelay: (index * 0.1) + 's' }"
                                >
                                    <div class="prize-item-header">
                                        <span class="prize-item-number">{{ prize.place }} место</span>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label">Название приза</label>
                                        <input type="text" class="form-input" v-model="prize.title" required>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label">Описание приза (опционально)</label>
                                        <textarea class="form-textarea" v-model="prize.description"></textarea>
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Спонсоры (опционально)</label>
                                <div v-for="(sponsor, index) in contestForm.sponsors" :key="index" class="sponsor-item">
                                    <input 
                                        type="text" 
                                        class="form-input" 
                                        v-model="sponsor.channelId"
                                        placeholder="ID канала"
                                    >
                                    <input 
                                        type="text" 
                                        class="form-input" 
                                        v-model="sponsor.channelTitle"
                                        placeholder="Название канала"
                                    >
                                    <button 
                                        type="button" 
                                        @click="removeSponsor(index)" 
                                        class="btn btn-error btn-sm"
                                    >
                                        Удалить
                                    </button>
                                </div>
                                <button type="button" @click="addSponsor" class="btn btn-secondary btn-sm">
                                    + Добавить спонсора
                                </button>
                            </div>
                            <div class="form-group">
                                <label class="form-label" style="display: flex; align-items: center; gap: 0.5rem;">
                                    <input 
                                        type="checkbox" 
                                        v-model="contestForm.requireYoutubeSubscription"
                                        style="width: auto;"
                                    >
                                    <span>Требовать подписку на YouTube канал</span>
                                </label>
                                <small class="text-secondary" style="display: block; margin-top: 0.5rem;">
                                    Если отмечено, участники должны быть подписаны на YouTube канал, указанный в настройках выбранного Telegram канала
                                </small>
                            </div>
                            <div class="form-group" v-if="contestForm.requireYoutubeSubscription">
                                <label class="form-label">Минимальное количество дней подписки на YouTube</label>
                                <input 
                                    type="number" 
                                    class="form-input" 
                                    v-model.number="contestForm.youtubeSubscriptionDaysRequired"
                                    min="0" 
                                    max="365"
                                    placeholder="0"
                                >
                                <small class="text-secondary" style="display: block; margin-top: 0.5rem;">
                                    Минимальное количество дней, которое участник должен быть подписан на YouTube канал (0 = проверка не требуется)
                                </small>
                            </div>
                            <div style="position: sticky; bottom: 4.5rem; margin-top: 1.5rem; padding-top: 1.5rem;">
                                <button type="submit" class="action-button" style="white-space: nowrap; overflow: visible; text-overflow: clip;">Создать конкурс</button>
                            </div>
                        </form>
                    </div>
                </div>
                </transition>
                </transition>
                
                <!-- Секция статистики -->
                <transition name="slide">
                    <div v-if="activeTab === 'stats'" class="admin-section active" key="stats">
                    <h2 class="section-title">Статистика</h2>
                    <div class="admin-card">
                        <div class="form-group">
                            <label class="form-label">Выберите конкурс</label>
                            <select class="form-select" v-model="selectedContestForStats" @change="loadStats">
                                <option :value="null">Выберите конкурс...</option>
                                <option v-for="contest in contests" :key="contest.id" :value="contest.id">
                                    {{ contest.title }}
                                </option>
                            </select>
                        </div>
                    </div>
                    <div v-if="loading.stats" class="loading">
                        <div class="spinner"></div>
                        <span>Загрузка...</span>
                    </div>
                    <div v-else-if="!selectedContestForStats" class="admin-card">
                        <p class="text-secondary text-center">Выберите конкурс для просмотра статистики</p>
                    </div>
                    <div v-else-if="stats" class="stats-grid">
                        <div 
                            class="stats-card"
                            :style="{ animationDelay: '0.1s' }"
                        >
                            <div class="stats-card-label">Участников</div>
                            <div class="stats-card-value">{{ stats.participants_count || 0 }}</div>
                        </div>
                        <div 
                            class="stats-card"
                            :style="{ animationDelay: '0.2s' }"
                        >
                            <div class="stats-card-label">Призовых мест</div>
                            <div class="stats-card-value">{{ stats.prize_count || 0 }}</div>
                        </div>
                        <div 
                            class="stats-card"
                            :style="{ animationDelay: '0.3s' }"
                        >
                            <div class="stats-card-label">Статус</div>
                            <div class="stats-card-value" style="font-size: 1.25rem;">{{ stats.status }}</div>
                        </div>
                    </div>
                </div>
                </transition>
            </div>
            
            <!-- Модальное окно добавления канала -->
            <transition name="fade">
                <div v-if="showAddChannelModal" class="modal-overlay" @click.self="closeAddChannelModal" key="modal">
                <div class="modal-content" @click.stop>
                    <div class="modal-header">
                        <h3 class="modal-title">Добавить канал</h3>
                        <button @click="closeAddChannelModal" class="modal-close">✕</button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="addChannel" class="admin-form">
                            <div class="form-group">
                                <label class="form-label">Username канала (@username)</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.username"
                                    @blur="resolveChannelUsername"
                                    @keyup.enter="resolveChannelUsername"
                                    placeholder="@example_channel" 
                                    :disabled="channelForm.resolving"
                                    required
                                >
                                <small class="text-secondary" style="display: block; margin-top: 0.5rem;">
                                    Введите username канала, ID и название заполнятся автоматически
                                </small>
                            </div>
                            <div class="form-group">
                                <label class="form-label">ID канала</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.channelId"
                                    readonly 
                                    style="background: rgba(255, 255, 255, 0.1);"
                                    required
                                >
                            </div>
                            <div class="form-group">
                                <label class="form-label">Название канала</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.channelTitle"
                                    readonly 
                                    style="background: rgba(255, 255, 255, 0.1);"
                                    required
                                >
                            </div>
                            <div class="form-group">
                                <label class="form-label">YouTube канал ID (опционально)</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.youtubeChannelId"
                                    placeholder="ID YouTube канала (например: UC...) или URL канала"
                                >
                                <small class="text-secondary" style="display: block; margin-top: 0.5rem;">
                                    Если указан, при создании конкурса можно будет требовать подписку на этот YouTube канал
                                </small>
                            </div>
                            <div class="modal-actions">
                                <button type="button" @click="closeAddChannelModal" class="btn btn-secondary">
                                    Отмена
                                </button>
                                <button type="submit" class="btn btn-primary" :disabled="channelForm.resolving">
                                    {{ channelForm.resolving ? 'Проверка...' : 'Добавить канал' }}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                </div>
            </transition>
            
            <!-- Модальное окно редактирования канала -->
            <transition name="fade">
                <div v-if="showEditChannelModal" class="modal-overlay" @click.self="closeEditChannelModal" key="edit-modal">
                <div class="modal-content" @click.stop>
                    <div class="modal-header">
                        <h3 class="modal-title">Редактировать канал</h3>
                        <button @click="closeEditChannelModal" class="modal-close">✕</button>
                    </div>
                    <div class="modal-body">
                        <form @submit.prevent="updateChannel" class="admin-form">
                            <div class="form-group">
                                <label class="form-label">Username канала</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.username"
                                    readonly
                                    style="background: rgba(255, 255, 255, 0.1);"
                                >
                            </div>
                            <div class="form-group">
                                <label class="form-label">ID канала</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.channelId"
                                    readonly 
                                    style="background: rgba(255, 255, 255, 0.1);"
                                    required
                                >
                            </div>
                            <div class="form-group">
                                <label class="form-label">Название канала</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.channelTitle"
                                    required
                                >
                            </div>
                            <div class="form-group">
                                <label class="form-label">YouTube канал ID (опционально)</label>
                                <input 
                                    type="text" 
                                    class="form-input" 
                                    v-model="channelForm.youtubeChannelId"
                                    placeholder="ID YouTube канала (например: UC...) или URL канала"
                                >
                                <small class="text-secondary" style="display: block; margin-top: 0.5rem;">
                                    Если указан, при создании конкурса можно будет требовать подписку на этот YouTube канал
                                </small>
                            </div>
                            <div class="modal-actions">
                                <button type="button" @click="closeEditChannelModal" class="btn btn-secondary">
                                    Отмена
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    Сохранить
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
                </div>
            </transition>
            
            <!-- Нижняя навигация -->
            <div class="admin-bottom-nav">
                <button 
                    @click="switchTab('contests')" 
                    :class="['admin-nav-item', { active: activeTab === 'contests' }]"
                >
                    <div class="admin-nav-item-icon">📋</div>
                    <div class="admin-nav-item-label">Конкурсы</div>
                </button>
                <button 
                    @click="switchTab('channels')" 
                    :class="['admin-nav-item', { active: activeTab === 'channels' }]"
                >
                    <div class="admin-nav-item-icon">📢</div>
                    <div class="admin-nav-item-label">Каналы</div>
                </button>
                <button 
                    @click="switchTab('create')" 
                    :class="['admin-nav-item', { active: activeTab === 'create' }]"
                >
                    <div class="admin-nav-item-icon">➕</div>
                    <div class="admin-nav-item-label">Создать</div>
                </button>
                <button 
                    @click="switchTab('stats')" 
                    :class="['admin-nav-item', { active: activeTab === 'stats' }]"
                >
                    <div class="admin-nav-item-icon">📊</div>
                    <div class="admin-nav-item-label">Статистика</div>
                </button>
            </div>
        </div>
    `
});

console.log('Монтирование приложения в #app...');

// Если Telegram WebApp не инициализирован, не монтируем приложение
if (!tg || !ADMIN_ID) {
    console.warn('Telegram WebApp не инициализирован, приложение не будет смонтировано');
    // Сообщение уже показано выше
} else {
    try {
        app.mount('#app');
        console.log('Приложение успешно смонтировано!');
    } catch (error) {
        console.error('Ошибка монтирования приложения:', error);
        const appEl = document.getElementById('app');
        if (appEl) {
            appEl.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: #0a0a0f; color: #fff; font-family: 'Inter', Arial, sans-serif;">
                    <div style="text-align: center; padding: 2rem; background: rgba(26, 26, 36, 0.9); border-radius: 1rem; border: 1px solid rgba(255, 255, 255, 0.1);">
                        <h1 style="font-size: 2rem; margin-bottom: 1rem;">❌ Ошибка монтирования</h1>
                        <p style="margin-bottom: 0.5rem;">Не удалось запустить админ-панель.</p>
                        <p style="color: #ff6b6b;">${error.message}</p>
                    </div>
                </div>
            `;
        }
    }
}
