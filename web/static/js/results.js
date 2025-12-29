/**
 * Результаты конкурса - полностью переработанная версия
 * Современные анимации с GSAP и Anime.js
 */

console.log('Loading results.js...');
console.log('Vue available:', typeof Vue !== 'undefined');

if (typeof Vue === 'undefined') {
    console.error('Vue.js не загружен!');
    const app = document.getElementById('app');
    if (app) {
        app.innerHTML = '<div style="padding: 2rem; color: red; text-align: center;">Ошибка: Vue.js не загружен</div>';
    }
} else {
    const { createApp } = Vue;

    let tg;
    try {
        if (typeof Telegram !== 'undefined' && Telegram.WebApp) {
            tg = Telegram.WebApp;
            tg.ready();
            tg.expand();
        }
    } catch (error) {
        console.error('Ошибка инициализации Telegram WebApp:', error);
    }

    const urlParams = new URLSearchParams(window.location.search);
    const contestId = urlParams.get('contest_id');

    // Импортируем функции напрямую, если модули не загружаются
    async function getContestInfo(contestId) {
        const response = await fetch(`/api/contests/${contestId}/info`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Конкурс не найден');
        }
        return await response.json();
    }

    async function getWinners(contestId) {
        const response = await fetch(`/api/contests/${contestId}/winners`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Результаты не найдены');
        }
        return await response.json();
    }

    const resultsApp = createApp({
    data() {
        return {
            contestId: contestId ? parseInt(contestId) : null,
            contest: null,
            winners: [],
            state: 'loading',
            errorMessage: ''
        };
    },
    
    async mounted() {
        console.log('Vue mounted, checking contest ID...');
        
        if (!this.contestId) {
            this.showError('Не указан ID конкурса');
            return;
        }
        
        // Проверка Telegram WebApp (необязательна для результатов, но желательна)
        if (typeof Telegram === 'undefined' || !Telegram.WebApp) {
            console.warn('Telegram WebApp API недоступен, продолжаем без него');
        } else {
            const tg = Telegram.WebApp;
            tg.ready();
            tg.expand();
        }
        
        // Анимация появления контейнера
        if (typeof gsap !== 'undefined') {
            gsap.from('.webapp-container', {
                opacity: 0,
                y: 20,
                duration: 0.6,
                ease: 'power3.out'
            });
        }
        
        await this.loadData();
    },
    
    methods: {
        async loadData() {
            try {
                this.state = 'loading';
                
                const [contestData, winnersData] = await Promise.all([
                    getContestInfo(this.contestId),
                    getWinners(this.contestId).catch(() => [])
                ]);
                
                this.contest = contestData;
                this.winners = winnersData;
                
                if (this.winners.length === 0) {
                    const isFinished = this.contest && 
                        (this.contest.status === 'finished' || this.contest.status === 'results_published');
                    
                    if (isFinished) {
                        this.showError('Конкурс завершен, но победители не определены');
                    } else {
                        this.showError('Победители еще не определены');
                    }
                    return;
                }
                
                this.winners.sort((a, b) => a.place - b.place);
                
                // Увеличенная задержка для более длительного прелоадера
                setTimeout(() => {
                    this.state = 'winners';
                    
                    if (tg && tg.HapticFeedback) {
                        tg.HapticFeedback.notificationOccurred('success');
                    }
                    
                    // Анимация появления контента
                    this.$nextTick(() => {
                        this.animateContestInfo();
                        // Небольшая задержка перед анимацией победителей для плавности
                        setTimeout(() => {
                            this.animateWinners();
                        }, 200);
                    });
                }, 1200);
            } catch (error) {
                this.showError(error.message || 'Ошибка загрузки данных');
            }
        },
        
        animateContestInfo() {
            if (typeof gsap === 'undefined') return;
            
            const card = document.querySelector('.content-card[key="contest-info"]');
            if (card) {
                gsap.fromTo(card, {
                    opacity: 0,
                    y: 30,
                    scale: 0.95
                }, {
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    duration: 0.8,
                    ease: 'power3.out'
                });
            }
        },
        
        animateWinners() {
            const cards = document.querySelectorAll('.winner-card');
            if (!cards.length) return;
            
            // Более плавная анимация появления карточек
            if (typeof anime !== 'undefined') {
                anime({
                    targets: cards,
                    opacity: [0, 1],
                    translateY: [40, 0],
                    scale: [0.95, 1],
                    delay: anime.stagger(100, { start: 0 }),
                    duration: 1200,
                    easing: 'easeOutCubic'
                });
            } else if (typeof gsap !== 'undefined') {
                // Fallback на GSAP с более плавными параметрами
                cards.forEach((card, index) => {
                    gsap.fromTo(card, {
                        opacity: 0,
                        y: 40,
                        scale: 0.95
                    }, {
                        opacity: 1,
                        y: 0,
                        scale: 1,
                        duration: 1,
                        delay: index * 0.1,
                        ease: 'power2.out'
                    });
                });
            }
        },
        
        showError(message) {
            this.errorMessage = message;
            this.state = 'error';
            
            if (tg && tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('error');
            }
            
            this.$nextTick(() => {
                if (typeof anime !== 'undefined') {
                    const errorCard = document.querySelector('.content-card[key="error"]');
                    if (errorCard) {
                        anime({
                            targets: errorCard,
                            opacity: [0, 1],
                            scale: [0.9, 1],
                            duration: 600,
                            easing: 'easeOutElastic(1, .6)'
                        });
                    }
                }
            });
        },
        
        getPlaceEmoji(place) {
            const emojis = { 1: '🥇', 2: '🥈', 3: '🥉' };
            return emojis[place] || '🏆';
        },
        
        getPlaceText(place) {
            const forms = ['', 'первое', 'второе', 'третье'];
            return place <= 3 ? forms[place] : `${place}-е`;
        },
        
        openUserLink(url) {
            // Используем Telegram WebApp API для открытия ссылок, если доступен
            if (typeof Telegram !== 'undefined' && Telegram.WebApp && Telegram.WebApp.openLink) {
                Telegram.WebApp.openLink(url);
            } else {
                // Fallback для обычного браузера
                window.open(url, '_blank');
            }
        },
        
        getPlaceColor(place) {
            const colors = {
                1: 'rgba(255, 215, 0, 0.2)',
                2: 'rgba(192, 192, 192, 0.2)',
                3: 'rgba(205, 127, 50, 0.2)'
            };
            return colors[place] || 'rgba(99, 102, 241, 0.15)';
        }
    },
    
    template: `
        <div class="webapp-container">
            <div class="webapp-header">
                <div class="webapp-header-title">
                    <span>🏆</span>
                    <span>Результаты</span>
                </div>
                <div v-if="contestId" class="pill info">ID #{{ contestId }}</div>
            </div>
            
            <div class="webapp-content">
                <transition name="fade">
                    <div v-if="state === 'loading'" class="loading-overlay" key="loading">
                        <div class="loading">
                            <div class="spinner"></div>
                            <div class="loader-label">Определяем победителей...</div>
                        </div>
                    </div>
                </transition>
                
                <div :style="{ opacity: state === 'loading' ? 0 : 1, transition: 'opacity 0.25s ease' }">
                    <transition name="fade">
                        <div v-if="contest" class="content-card" key="contest-info">
                            <div v-if="contest.image_path" style="margin-bottom: 1rem;">
                                <img :src="'/' + contest.image_path" alt="Изображение конкурса" style="width: 100%; border-radius: 0.5rem; max-height: 300px; object-fit: cover;">
                            </div>
                            <div class="flex-between mb-2">
                                <div>
                                    <div class="content-card-title">{{ contest.title }}</div>
                                    <div v-if="contest.description" class="content-card-subtitle">
                                        {{ contest.description }}
                                    </div>
                                    <div v-if="contest.participants_count !== undefined" class="content-card-subtitle" style="margin-top: 0.5rem; opacity: 0.8;">
                                        Участников: <strong>{{ contest.participants_count }}</strong>
                                    </div>
                                </div>
                                <div class="pill info">
                                    {{ contest.status === 'finished' || contest.status === 'results_published' ? 'Завершен' : 'Результаты' }}
                                </div>
                            </div>
                        </div>
                    </transition>
                    
                    <transition name="slide">
                        <div v-if="state === 'winners'" key="winners">
                            <div class="content-card stack">
                                <div class="flex-between mb-2">
                                    <div class="content-card-title">Победители</div>
                                    <div class="pill success">Определены</div>
                                </div>
                                <div class="stack">
                                    <div 
                                        v-for="(winner, index) in winners" 
                                        :key="winner.place"
                                        class="winner-card"
                                        :style="{ background: getPlaceColor(winner.place) }"
                                    >
                                        <div class="winner-place">
                                            <span>{{ getPlaceEmoji(winner.place) }}</span>
                                            <span>{{ getPlaceText(winner.place) }} место</span>
                                        </div>
                                        <div class="winner-prize">{{ winner.title }}</div>
                                        <div v-if="winner.description" class="micro">
                                            {{ winner.description }}
                                        </div>
                                        <div class="winner-name">
                                            Победитель: 
                                            <strong v-if="winner.winner_username">
                                                <a @click.prevent="openUserLink('https://t.me/' + winner.winner_username)" href="#" style="color: inherit; text-decoration: underline; cursor: pointer;">@{{ winner.winner_username }}</a>
                                            </strong>
                                            <strong v-else-if="winner.winner_firstname">
                                                <a @click.prevent="openUserLink('tg://user?id=' + winner.winner_user_id)" href="#" style="color: inherit; text-decoration: underline; cursor: pointer;">{{ winner.winner_firstname }}</a>
                                            </strong>
                                            <strong v-else>не указан</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </transition>
                    
                    <transition name="fade">
                        <div v-if="state === 'error'" class="content-card" key="error">
                            <div class="status-block stack">
                                <div class="status-icon">📋</div>
                                <div class="status-title">Информация</div>
                                <p class="status-description">{{ errorMessage }}</p>
                                <button @click="loadData" class="btn btn-secondary btn-inline">
                                    Обновить
                                </button>
                            </div>
                        </div>
                    </transition>
                </div>
            </div>
        </div>
    `
    });

    console.log('Mounting Vue app to #app...');
    const appElement = document.getElementById('app');
    if (!appElement) {
        console.error('Element #app not found!');
    } else {
        console.log('Element #app found, mounting Vue...');
        resultsApp.mount('#app');
    }
}
