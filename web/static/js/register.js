/**
 * Регистрация в конкурсе с авторизацией через YouTube
 */
const { createApp } = Vue;

// Константы
const AUTH_POLL_INTERVAL = 3000; // 3 секунды
const AUTH_TIMEOUT = 300000; // 5 минут

createApp({
  data() {
    return {
      // Состояние загрузки
      loading: true,
      error: null,
      
      // Данные конкурса
      contestId: null,
      contestData: null,
      
      // Данные пользователя Telegram
      userId: null,
      username: null,
      firstName: null,
      initData: null,
      
      // YouTube авторизация
      youtubeConnected: false,
      youtubeChannelId: null,
      youtubeChannelTitle: null,
      youtubeAuthInProgress: false,
      youtubeSubscribed: false, // Подписан ли пользователь на YouTube канал конкурса
      
      // Регистрация
      registrationComplete: false,
      registrationError: null,
      registrationNumber: null,
      registeredAt: null,
      
      // Polling
      pollIntervalId: null,
      pollTimeoutId: null
    };
  },
  
  computed: {
    /**
     * Можно ли завершить регистрацию
     */
    canRegister() {
      return this.youtubeConnected && !this.registrationComplete;
    },
    
    /**
     * Telegram WebApp API
     */
    tg() {
      return window.Telegram?.WebApp;
    },
    
    /**
     * URL YouTube канала для подписки
     */
    youtubeChannelUrl() {
      if (!this.contestData?.youtube_channel_id) {
        return null;
      }
      
      const channelId = this.contestData.youtube_channel_id;
      
      // Если это handle канала (@username)
      if (channelId.startsWith('@')) {
        return `https://youtube.com/${channelId}`;
      }
      
      // Если это полный URL
      if (channelId.startsWith('http')) {
        return channelId;
      }
      
      // Если это стандартный ID канала (UC...)
      if (channelId.startsWith('UC') || channelId.startsWith('HC')) {
        return `https://youtube.com/channel/${channelId}`;
      }
      
      // По умолчанию пробуем как handle
      return `https://youtube.com/@${channelId}`;
    },
    
    /**
     * Требуется ли подписка на YouTube канал
     */
    requiresYouTubeSubscription() {
      return !!this.contestData?.youtube_channel_id;
    },
    
    /**
     * Количество дней подписки, которое требуется
     */
    youtubeSubscriptionDaysRequired() {
      return this.contestData?.youtube_subscription_days_required || 0;
    },
    
    /**
     * Форматированная дата подведения итогов конкурса
     */
    contestEndDateFormatted() {
      if (!this.contestData?.end_date) {
        return null;
      }
      
      const date = new Date(this.contestData.end_date);
      const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Europe/Kiev',
        timeZoneName: 'short'
      };
      
      return date.toLocaleDateString('ru-RU', options);
    }
  },
  
  async mounted() {
    // Анимация появления контейнера
    if (typeof gsap !== 'undefined') {
      gsap.from('.webapp-container', {
        opacity: 0,
        y: 20,
        duration: 0.6,
        ease: 'power3.out'
      });
    }
    
    await this.initializeApp();
    
    // Анимации для плавного появления элементов
    this.$nextTick(() => {
      this.animateContent();
    });
  },
  
  beforeUnmount() {
    this.stopAuthPolling();
    window.removeEventListener('message', this.handleOAuthMessage);
  },
  
  methods: {
    /**
     * Инициализация приложения
     */
    async initializeApp() {
      try {
        // Проверка доступности Telegram WebApp
        if (!this.tg) {
          throw new Error('Telegram WebApp API недоступен');
        }
        
        this.tg.ready();
        this.tg.expand();
        
        // Применяем тему Telegram
        this.applyTelegramTheme();
        
        // Получаем данные пользователя
        this.extractUserData();
        
        // Получаем ID конкурса
        this.extractContestId();
        
        // Загружаем данные конкурса
        await this.loadContestData();
        
        // Проверяем существующую регистрацию
        await this.checkExistingRegistration();
        
        // Проверяем подписку на YouTube канал, если требуется (после проверки регистрации, т.к. там может установиться youtubeConnected)
        if (this.requiresYouTubeSubscription && this.youtubeConnected) {
          await this.checkYouTubeSubscription();
        }
        
        // Слушаем сообщения от OAuth окна
        window.addEventListener('message', this.handleOAuthMessage);
        
        this.loading = false;
        
        // Анимация успешной регистрации, если уже зарегистрирован
        if (this.registrationComplete) {
          this.$nextTick(() => {
            setTimeout(() => this.animateSuccess(), 300);
          });
        }
        
      } catch (err) {
        console.error('Initialization error:', err);
        this.error = err.message;
        this.loading = false;
      }
    },
    
    /**
     * Применить тему Telegram
     */
    applyTelegramTheme() {
      const theme = this.tg.themeParams;
      const root = document.documentElement;
      
      root.style.setProperty('--tg-theme-bg-color', theme.bg_color || '#0a0a0f');
      root.style.setProperty('--tg-theme-text-color', theme.text_color || '#ffffff');
      root.style.setProperty('--tg-theme-button-color', theme.button_color || '#667eea');
    },
    
    /**
     * Извлечь данные пользователя из Telegram
     */
    extractUserData() {
      const user = this.tg.initDataUnsafe?.user;
      
      if (!user) {
        throw new Error('Не удалось получить данные пользователя');
      }
      
      this.userId = user.id;
      this.username = user.username;
      this.firstName = user.first_name;
      this.initData = this.tg.initData;
    },
    
    /**
     * Извлечь ID конкурса из URL
     */
    extractContestId() {
      const urlParams = new URLSearchParams(window.location.search);
      const contestId = parseInt(urlParams.get('contest_id'));
      
      if (!contestId) {
        throw new Error('ID конкурса не указан');
      }
      
      this.contestId = contestId;
    },
    
    /**
     * Загрузить данные конкурса
     */
    async loadContestData() {
      try {
        const response = await fetch(`/api/contests/${this.contestId}`);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.detail || `Ошибка загрузки конкурса (${response.status})`;
          
          if (response.status === 404) {
            throw new Error('Конкурс не найден. Возможно, он был удален или еще не создан.');
          } else if (response.status === 400) {
            // Конкурс недоступен, закончен или не опубликован
            throw new Error(errorMessage);
          }
          
          throw new Error(errorMessage);
        }
        
        this.contestData = await response.json();
      } catch (err) {
        console.error('Error loading contest:', err);
        throw err; // Пробрасываем оригинальную ошибку с понятным сообщением
      }
    },
    
    /**
     * Проверить подписку на YouTube канал конкурса
     */
    async checkYouTubeSubscription() {
      if (!this.contestData?.youtube_channel_id || !this.userId) {
        return;
      }
      
      try {
        const response = await fetch(
          `/api/contests/${this.contestId}/check-subscription?user_id=${this.userId}`
        );
        
        if (response.ok) {
          const data = await response.json();
          this.youtubeSubscribed = data.youtube_subscribed === true;
        }
      } catch (error) {
        console.error('Ошибка проверки подписки на YouTube:', error);
        // В случае ошибки показываем ссылку (на всякий случай)
        this.youtubeSubscribed = false;
      }
    },
    
    /**
     * Проверить существующую регистрацию
     */
    async checkExistingRegistration() {
      try {
        const response = await fetch(
          `/api/contests/${this.contestId}/participants/${this.userId}`,
          {
            headers: {
              'X-Telegram-Init-Data': this.initData
            }
          }
        );
        
        if (response.ok) {
          const data = await response.json();
          
          if (data) {
            this.registrationComplete = true;
            this.registrationNumber = data.registration_number;
            this.registeredAt = data.registered_at;
            this.youtubeConnected = true;
            this.youtubeChannelId = data.youtube_channel_id;
            this.youtubeChannelTitle = data.youtube_channel_title;
            // Если пользователь уже зарегистрирован, не проверяем авторизацию YouTube
            return;
          }
        }
      } catch (err) {
        console.error('Error checking registration:', err);
        // Не критично, продолжаем работу
      }
      
      // Проверяем сохраненные credentials при загрузке страницы только если не зарегистрирован
      if (!this.registrationComplete) {
        await this.checkAuthStatus();
        // После проверки авторизации проверяем подписку, если YouTube подключен
        if (this.requiresYouTubeSubscription && this.youtubeConnected) {
          await this.checkYouTubeSubscription();
        }
      }
      
      // Проверяем параметры успешной авторизации из URL
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('youtube_auth_success') === 'true') {
        // Запускаем проверку статуса авторизации
        await this.checkAuthStatus();
        // Очищаем параметр из URL
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('youtube_auth_success');
        window.history.replaceState({}, document.title, newUrl.toString());
      }
    },
    
    /**
     * Начать авторизацию YouTube
     */
    async startYouTubeAuth() {
      if (this.youtubeAuthInProgress) return;
      
      this.youtubeAuthInProgress = true;
      this.error = null;
      
      try {
        const authUrl = this.buildAuthUrl();
        
        // Показываем предупреждение пользователю
        this.tg.showAlert(
          'Сейчас откроется страница YouTube для авторизации. После завершения вернитесь в бот.',
          () => {
            // Открываем OAuth в браузере
            this.tg.openLink(authUrl);
            
            // Запускаем polling
            this.startAuthPolling();
          }
        );
        
      } catch (err) {
        console.error('Error starting auth:', err);
        this.error = 'Не удалось запустить авторизацию YouTube';
        this.youtubeAuthInProgress = false;
      }
    },
    
    /**
     * Построить URL авторизации
     */
    buildAuthUrl() {
      const params = new URLSearchParams({
        contest_id: this.contestId,
        user_id: this.userId,
        _auth: this.initData
      });
      
      return `${window.location.origin}/api/youtube/auth?${params.toString()}`;
    },
    
    /**
     * Запустить polling статуса авторизации
     */
    startAuthPolling() {
      // Polling каждые 3 секунды
      this.pollIntervalId = setInterval(async () => {
        await this.checkAuthStatus();
      }, AUTH_POLL_INTERVAL);
      
      // Таймаут через 5 минут
      this.pollTimeoutId = setTimeout(() => {
        this.stopAuthPolling();
        
        if (this.youtubeAuthInProgress && !this.youtubeConnected) {
          this.youtubeAuthInProgress = false;
          this.error = 'Время ожидания авторизации истекло. Попробуйте еще раз.';
        }
      }, AUTH_TIMEOUT);
    },
    
    /**
     * Остановить polling
     */
    stopAuthPolling() {
      if (this.pollIntervalId) {
        clearInterval(this.pollIntervalId);
        this.pollIntervalId = null;
      }
      
      if (this.pollTimeoutId) {
        clearTimeout(this.pollTimeoutId);
        this.pollTimeoutId = null;
      }
    },
    
    /**
     * Проверить статус авторизации
     */
    async checkAuthStatus() {
      try {
        const response = await fetch(
          `/api/youtube/check-auth?user_id=${this.userId}&contest_id=${this.contestId}`,
          {
            headers: {
              'X-Telegram-Init-Data': this.initData
            }
          }
        );
        
        if (!response.ok) return;
        
        const data = await response.json();
        
        if (data.authenticated) {
          this.handleAuthSuccess(data);
        }
        
      } catch (err) {
        console.error('Error checking auth status:', err);
      }
    },
    
    /**
     * Обработать успешную авторизацию
     */
    async handleAuthSuccess(data) {
      this.stopAuthPolling();
      
      this.youtubeConnected = true;
      this.youtubeChannelId = data.channel_id;
      this.youtubeChannelTitle = data.channel_title;
      this.youtubeAuthInProgress = false;
      
      // Анимация успешного подключения
      this.$nextTick(() => {
        const youtubeCard = document.querySelector('.content-card[key="youtube-auth"]');
        if (youtubeCard && typeof anime !== 'undefined') {
          anime({
            targets: youtubeCard,
            scale: [1, 1.02, 1],
            duration: 600,
            easing: 'easeOutElastic(1, .6)'
          });
        }
      });
      
      // Показываем alert только если это не автоматическая проверка при загрузке
      if (this.pollIntervalId) {
        this.tg.showAlert('✅ Авторизация YouTube успешно завершена!');
      }
      
      // Проверяем подписку на YouTube канал конкурса, если требуется
      if (this.requiresYouTubeSubscription) {
        await this.checkYouTubeSubscription();
      }
    },
    
    /**
     * Обработать сообщения от OAuth окна (альтернативный метод)
     */
    handleOAuthMessage(event) {
      if (!event.data || typeof event.data !== 'object') return;
      
      if (event.data.type === 'youtube_auth_success') {
        this.handleAuthSuccess({
          channel_id: event.data.youtube_channel_id,
          channel_title: event.data.youtube_channel_title || 'YouTube Channel'
        });
      } else if (event.data.type === 'youtube_auth_error') {
        this.error = event.data.message || 'Ошибка авторизации YouTube';
        this.youtubeAuthInProgress = false;
        this.stopAuthPolling();
      }
    },
    
    /**
     * Завершить регистрацию
     */
    async completeRegistration() {
      if (!this.canRegister) return;
      
      this.loading = true;
      this.registrationError = null;
      
      try {
        const response = await fetch(`/api/contests/${this.contestId}/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': this.initData
          },
          body: JSON.stringify({
            user_id: this.userId,
            username: this.username,
            youtube_channel_id: this.youtubeChannelId
          })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Ошибка регистрации');
        }
        
        this.registrationComplete = true;
        
        // Анимация успешной регистрации
        this.$nextTick(() => {
          if (typeof anime !== 'undefined') {
            const registerCard = document.querySelector('.content-card[key="register"]');
            if (registerCard) {
              anime({
                targets: registerCard,
                scale: [1, 1.1, 1],
                rotateZ: [0, 5, -5, 0],
                duration: 800,
                easing: 'easeOutElastic(1, .6)',
                complete: () => {
                  // Автоматически закрываем WebApp после анимации
                  setTimeout(() => {
                    if (this.tg && this.tg.close) {
                      this.tg.close();
                    }
                  }, 300);
                }
              });
            }
          } else {
            // Fallback - просто закрываем
            setTimeout(() => {
              if (this.tg && this.tg.close) {
                this.tg.close();
              }
            }, 500);
          }
        });
        
      } catch (err) {
        console.error('Registration error:', err);
        this.registrationError = err.message;
      } finally {
        this.loading = false;
      }
    },
    
    /**
     * Отключить YouTube
     */
    disconnectYouTube() {
      this.tg.showConfirm(
        'Вы уверены, что хотите отключить YouTube канал?',
        (confirmed) => {
          if (confirmed) {
            this.youtubeConnected = false;
            this.youtubeChannelId = null;
            this.youtubeChannelTitle = null;
          }
        }
      );
    },
    
    /**
     * Посмотреть результаты конкурса
     */
    viewResults() {
      if (this.contestId) {
        // Редиректим в том же окне WebApp
        window.location.href = `/results?contest_id=${this.contestId}`;
      }
    },
    
    /**
     * Форматировать дату регистрации
     */
    formatDate(dateString) {
      if (!dateString) return '';
      
      try {
        const date = new Date(dateString);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `Зарегистрирован: ${day}.${month}.${year} в ${hours}:${minutes}`;
      } catch (e) {
        return dateString;
      }
    }
  },
  
  template: `
    <div class="webapp-container">
      <div class="webapp-header">
        <div class="webapp-header-title">
          <span>🎯</span>
          <span>Регистрация</span>
        </div>
        <div v-if="contestId" class="pill info">ID #{{ contestId }}</div>
      </div>

      <div class="webapp-content">
        <transition name="fade">
          <div v-if="loading" class="loading-overlay" key="loading">
            <div class="loading">
              <div class="spinner"></div>
              <div class="loader-label">Загрузка...</div>
            </div>
          </div>
        </transition>

        <div :style="{ opacity: loading ? 0 : 1, transition: 'opacity 0.25s ease' }">
          <div v-if="error" class="content-card">
            <div class="status-block stack">
              <div class="status-icon">📋</div>
              <div class="status-title">Конкурс недоступен</div>
              <p class="status-description">{{ error }}</p>
              <div class="stack">
                <div class="small muted" v-if="error.includes('завершен') || error.includes('закончен')">
                  Конкурс завершен. Можно открыть итоги прямо здесь.
                </div>
                <button
                  v-if="error.includes('завершен') || error.includes('закончен')"
                  class="btn btn-secondary"
                  @click="viewResults"
                >
                  📊 Посмотреть результаты
                </button>
              </div>
            </div>
          </div>

          <template v-else>
            <transition name="fade">
              <div v-if="registrationComplete" class="content-card" key="already-registered">
                <div class="status-block stack">
                  <div class="status-icon">✅</div>
                  <div class="status-title">Вы уже зарегистрированы</div>
                  <div v-if="contestEndDateFormatted" class="text-center" style="margin-top: 0.5rem; opacity: 0.8; font-size: 0.9rem;">
                    Итоги будут подведены: {{ contestEndDateFormatted }}
                  </div>
                  <button class="btn" @click="viewResults">
                    Открыть результаты
                  </button>
                </div>
              </div>
            </transition>

            <template v-if="!registrationComplete">
              <transition name="fade">
                <div v-if="contestData" class="content-card" key="contest-info">
                  <div class="flex-between mb-2">
                    <div>
                      <div class="content-card-title">{{ contestData.title }}</div>
                      <div v-if="contestData.description" class="content-card-subtitle">
                        {{ contestData.description }}
                      </div>
                    </div>
                    <div class="pill info">Конкурс</div>
                  </div>
                </div>
              </transition>

              <transition name="slide">
                <div class="content-card stack" key="youtube-auth">
                  <div v-if="!youtubeConnected" class="flex-between">
                    <div>
                      <div class="content-card-title">Подключите YouTube</div>
                      <div class="content-card-subtitle">Канал нужен для участия</div>
                    </div>
                    <div class="pill info">Не подключен</div>
                  </div>

                  <div v-else class="text-center">
                    <div class="pill success" style="display: inline-block;">
                      {{ youtubeChannelTitle || 'Подключен' }}
                    </div>
                  </div>

                  <div v-if="requiresYouTubeSubscription && youtubeChannelUrl && !youtubeSubscribed && youtubeConnected" class="stack" style="margin-bottom: 1rem;">
                    <div class="info-badge" style="background: rgba(255, 0, 0, 0.1); border: 1px solid rgba(255, 0, 0, 0.3);">
                      <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span>📺</span>
                        <div style="flex: 1;">
                          <div style="font-weight: 600; margin-bottom: 0.25rem;">Подпишитесь на YouTube канал</div>
                          <a 
                            :href="youtubeChannelUrl" 
                            target="_blank" 
                            rel="noopener noreferrer"
                            style="color: #4A9EFF; text-decoration: underline; font-size: 0.9rem;"
                            @click.stop
                          >
                            Открыть канал для подписки →
                          </a>
                          <div v-if="youtubeSubscriptionDaysRequired > 0" style="font-size: 0.85rem; margin-top: 0.25rem; opacity: 0.8;">
                            Требуется подписка минимум на {{ youtubeSubscriptionDaysRequired }} {{ youtubeSubscriptionDaysRequired === 1 ? 'день' : youtubeSubscriptionDaysRequired < 5 ? 'дня' : 'дней' }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-if="requiresYouTubeSubscription && youtubeSubscribed && youtubeConnected" class="stack" style="margin-bottom: 1rem;">
                    <div class="info-badge" style="background: rgba(76, 175, 80, 0.1); border: 1px solid rgba(76, 175, 80, 0.3);">
                      <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span>✅</span>
                        <div style="flex: 1;">
                          <div style="font-weight: 600;">Вы подписаны на YouTube канал</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="!youtubeConnected" class="stack">
                    <button
                      @click="startYouTubeAuth"
                      :disabled="youtubeAuthInProgress"
                      class="btn"
                    >
                      <span v-if="youtubeAuthInProgress" class="btn-spinner"></span>
                      {{ youtubeAuthInProgress ? 'Ожидаем авторизацию...' : '🔐 Подключить YouTube' }}
                    </button>
                    <div v-if="youtubeAuthInProgress" class="small text-center muted">
                      После авторизации вернитесь в бот, статус проверится автоматически.
                    </div>
                  </div>

                  <div v-else-if="!registrationComplete" class="stack">
                    <button
                      @click="disconnectYouTube"
                      class="btn btn-secondary"
                    >
                      Отключить
                    </button>
                  </div>
                </div>
              </transition>

              <transition name="fade">
                <div v-if="registrationError" class="content-card" key="reg-error">
                  <div class="alert">
                    <span class="alert-icon">⚠️</span>
                    <span>{{ registrationError }}</span>
                  </div>
                </div>
              </transition>

              <transition name="slide">
                <div class="content-card stack" key="register">
                  <button
                    @click="completeRegistration"
                    :disabled="!canRegister || loading"
                    class="btn"
                  >
                    <span v-if="loading" class="btn-spinner"></span>
                    {{ loading ? 'Регистрация...' : '🎉 Завершить регистрацию' }}
                  </button>
                  <div class="micro text-center">Нужно подключить YouTube перед регистрацией</div>
                </div>
              </transition>
            </template>
          </template>
        </div>
      </div>
    </div>
  `
}).mount('#app');
