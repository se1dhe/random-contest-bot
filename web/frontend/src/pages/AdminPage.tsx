import React, { Suspense, lazy, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { useTelegram } from '../hooks/useTelegram';
import { GlassCard } from '../components/ui/Cards';
import { Button } from '../components/ui/Button';
import {
    Plus,
    Settings,
    Radio,
    Trophy,
    Users,
    ChevronRight,
    ArrowLeft,
    Send,
    CheckCircle2,
    Clock,
    Youtube,
    Music2,
    Trash2,
    RefreshCw,
    AlertCircle
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

const GrowthChart = lazy(() =>
    import('../components/admin/GrowthChart').then((module) => ({ default: module.GrowthChart }))
);
const ContestForm = lazy(() =>
    import('../components/ContestForm').then((module) => ({ default: module.ContestForm }))
);
const ArchiveTab = lazy(() =>
    import('../components/admin/ArchiveTab').then((module) => ({ default: module.ArchiveTab }))
);
const JournalTab = lazy(() =>
    import('../components/admin/JournalTab').then((module) => ({ default: module.JournalTab }))
);
const DashboardQuickPanels = lazy(() =>
    import('../components/admin/DashboardQuickPanels').then((module) => ({ default: module.DashboardQuickPanels }))
);
const DashboardStatsGrid = lazy(() =>
    import('../components/admin/DashboardStatsGrid').then((module) => ({ default: module.DashboardStatsGrid }))
);
const SystemHealthPanel = lazy(() =>
    import('../components/admin/SystemHealthPanel').then((module) => ({ default: module.SystemHealthPanel }))
);

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

type AdminTab = 'dash' | 'contests' | 'archive' | 'journal' | 'channels';
const ADMIN_PREFERENCES_STORAGE_KEY = 'admin_page_preferences_v1';

export const AdminPage: React.FC = () => {
    const { initData, hapticFeedback, openLink, openTelegramLink } = useTelegram();
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<AdminTab>('dash');
    const [isCreating, setIsCreating] = useState(false);
    interface AdminContest {
        id: number;
        title: string;
        status: string;
        prize_count: number;
        participants_count?: number;
        end_date: string;
        publish_at?: string | null;
        prizes?: Array<{ id?: number; place: number; title?: string; description?: string }>;
        channel?: { channel_title?: string; channel_username?: string | null };
        require_youtube_subscription?: boolean;
        youtube_subscription_days_required?: number;
        require_tiktok_follow?: boolean;
        require_captcha?: boolean;
    }
    interface CreatedContest {
        id: number;
        title: string;
        status: string;
    }
    interface ContestPreview {
        contest_id: number;
        title: string;
        status: string;
        scheduled_for?: string | null;
        text: string;
        button_url?: string | null;
        has_image: boolean;
    }
    interface ResultsPreview {
        contest_id: number;
        title: string;
        status: string;
        text: string;
        button_url?: string | null;
        winners: Array<{
            place: number;
            title: string;
            winner_user_id?: number | null;
            winner_username?: string | null;
            winner_firstname?: string | null;
        }>;
    }
    interface RepublishDiff {
        contest_id: number;
        title: string;
        previous_text: string;
        current_text: string;
        button_url?: string | null;
        diff: string;
        has_changes: boolean;
        has_baseline?: boolean;
    }
    interface AdminHistoryItem {
        id: number;
        created_at: string;
        actor_user_id: number;
        action_type: string;
        target_type?: string | null;
        target_id?: string | null;
        status: string;
        contest_title?: string | null;
        message?: string | null;
        payload?: Record<string, unknown> | null;
    }
    interface AdminChannel {
        channel_id: number;
        channel_title: string;
        channel_username?: string | null;
    }
    interface AdminYoutubeChannel {
        channel_id: string;
        title: string;
        description?: string;
    }
    interface AdminTikTokChannel {
        channel_id: string;
        title: string;
        description?: string;
    }
    interface AnalyticsOverview {
        total_contests: number;
        active_contests: number;
        completed_contests: number;
        total_participants: number;
    }
    interface GrowthPoint {
        date: string;
        participants: number;
    }
    interface HealthService {
        status: 'ok' | 'warning' | 'error' | 'disabled';
        detail: string;
    }
    interface AnalyticsHealth {
        generated_at: string;
        services: {
            database: HealthService;
            redis: HealthService;
            bot_api: HealthService;
        };
        issues: {
            active_without_message_id: number;
            results_without_message_id: number;
            overdue_scheduled: number;
            finished_without_winners: number;
            total: number;
        };
        problematic_contests: Array<{
            contest_id: number;
            title: string;
            status: string;
            channel_title?: string | null;
            issue_type: string;
            detail: string;
            actionability: 'auto_repairable' | 'manual_attention';
        }>;
    }
    interface SubscriptionStatus {
        active: boolean;
        is_super_admin?: boolean;
        subscription?: {
            ends_at?: string | null;
            provider?: string;
            plan_code?: string;
        } | null;
        plan: {
            title: string;
            telegram_stars: number;
            fiat_cents: number;
            limits: {
                max_channels: number;
                max_active_contests: number;
                max_draft_contests: number;
                max_external_channels_per_platform: number;
                max_sponsors_per_contest: number;
                max_prizes_per_contest: number;
                max_image_mb: number;
            };
        };
        usage: {
            channels: number;
            active_contests: number;
            draft_contests: number;
            youtube_channels: number;
            tiktok_channels: number;
        };
    }
    interface PaginatedContestsResponse {
        items: AdminContest[];
        total: number;
        limit: number;
        offset: number;
    }
    const [selectedContest, setSelectedContest] = useState<AdminContest | null>(null);
    const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null);

    // Channel adding state
    const [addingChannelType, setAddingChannelType] = useState<'telegram' | 'youtube' | 'tiktok' | null>(null);
    const [newChannelInput, setNewChannelInput] = useState('');
    const [isAddingChannel, setIsAddingChannel] = useState(false);
    const [activeChannelId, setActiveChannelId] = useState<number | string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [scheduleAt, setScheduleAt] = useState('');
    const [preview, setPreview] = useState<ContestPreview | null>(null);
    const [resultsPreview, setResultsPreview] = useState<ResultsPreview | null>(null);
    const [republishDiff, setRepublishDiff] = useState<RepublishDiff | null>(null);
    const [contestSearch, setContestSearch] = useState('');
    const [contestFilter, setContestFilter] = useState<'all' | 'scheduled' | 'active' | 'draft' | 'finished' | 'results_published'>('all');
    const [contestPage, setContestPage] = useState(1);
    const [actionSearch, setActionSearch] = useState('');
    const [actionFilter, setActionFilter] = useState<'all' | 'contest' | 'channel' | 'youtube_channel' | 'tiktok_channel'>('all');
    const [growthDays, setGrowthDays] = useState<7 | 30 | 90>(30);
    const [paymentLoading, setPaymentLoading] = useState<'paykassa' | 'stars' | null>(null);

    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const contestPageSize = 20;

    const actionKey = (action: string, contestId?: number | string) =>
        contestId !== undefined ? `${action}:${contestId}` : action;

    const isActionLoading = (action: string, contestId?: number | string) =>
        actionLoadingKey === actionKey(action, contestId);

    const extractErrorMessage = (err: unknown, fallback: string) =>
        (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || fallback;

    const formatBulkSkippedSummary = (skipped: Array<{ contest_id?: number; reason?: string }> = []) => {
        if (!skipped.length) {
            return 'без пропусков';
        }

        const reasonLabel = (reason?: string) => {
            if (!reason) return 'неизвестная причина';
            if (reason === 'not_found') return 'не найден';
            if (reason === 'publish_failed') return 'ошибка публикации';
            if (reason === 'schedule_not_set') return 'нет отложенной публикации';
            if (reason.startsWith('invalid_status:')) {
                const status = reason.split(':')[1] || 'unknown';
                return `статус ${status}`;
            }
            return reason;
        };

        const grouped = skipped.reduce<Record<string, number>>((acc, item) => {
            const label = reasonLabel(item.reason);
            acc[label] = (acc[label] || 0) + 1;
            return acc;
        }, {});

        return Object.entries(grouped)
            .map(([label, count]) => `${label}: ${count}`)
            .join(', ');
    };

    const effectiveStatus = (contest: AdminContest) =>
        contest.status === 'draft' && contest.publish_at ? 'scheduled' : contest.status;

    const contestStatusPriority = (contest: AdminContest) => {
        const status = effectiveStatus(contest);
        switch (status) {
            case 'scheduled':
                return 0;
            case 'active':
                return 1;
            case 'draft':
                return 2;
            case 'finished':
                return 3;
            case 'results_published':
                return 4;
            default:
                return 5;
        }
    };

    const historyActionLabels: Record<string, string> = {
        contest_created: 'Конкурс создан',
        contest_deleted: 'Конкурс удален',
        contest_drawn: 'Розыгрыш проведен',
        contest_published: 'Конкурс опубликован',
        contest_results_published: 'Результаты опубликованы',
        contest_publish_scheduled: 'Публикация запланирована',
        contest_publish_schedule_canceled: 'Отложенная публикация отменена',
        contest_republished: 'Конкурс перепубликован',
        contest_duplicated: 'Создана копия конкурса',
        contest_post_edited: 'Пост конкурса обновлен',
        contest_repaired: 'Конкурс восстановлен',
        contest_participants_exported: 'Выгружен CSV участников',
        channel_created: 'Telegram-канал добавлен',
        channel_updated: 'Telegram-канал обновлен',
        channel_deleted: 'Telegram-канал удален',
        channel_reactivated: 'Telegram-канал восстановлен',
        youtube_channel_created: 'YouTube-канал добавлен',
        youtube_channel_deleted: 'YouTube-канал удален',
        tiktok_channel_created: 'TikTok-аккаунт добавлен',
        tiktok_channel_deleted: 'TikTok-аккаунт удален',
    };

    const formatHistoryDetails = (entry: AdminHistoryItem) => {
        const payload = entry.payload || {};

        if (entry.message) {
            return entry.message;
        }

        switch (entry.action_type) {
            case 'contest_created':
                return payload.title ? `Название: ${String(payload.title)}` : 'Создан новый конкурс';
            case 'contest_publish_scheduled':
                return payload.publish_at ? `Время публикации: ${new Date(String(payload.publish_at)).toLocaleString()}` : 'Публикация поставлена в очередь';
            case 'contest_drawn':
                return Array.isArray(payload.winners) ? `Определено победителей: ${payload.winners.length}` : 'Победители определены';
            case 'contest_participants_exported':
                return payload.participants_count !== undefined ? `Участников в выгрузке: ${String(payload.participants_count)}` : 'Участники экспортированы';
            case 'contest_republished':
                return 'Создана новая публикация конкурса в канале';
            case 'contest_duplicated':
                return payload.source_title ? `Копия конкурса: ${String(payload.source_title)}` : 'Создан новый конкурс из шаблона';
            case 'contest_post_edited':
                return 'Обновлен уже опубликованный пост конкурса';
            default:
                return null;
        }
    };

    useEffect(() => {
        setScheduleAt(selectedContest?.publish_at ? selectedContest.publish_at.slice(0, 16) : '');
        setPreview(null);
        setResultsPreview(null);
        setRepublishDiff(null);
    }, [selectedContest?.id, selectedContest?.publish_at]);

    useEffect(() => {
        setContestPage(1);
    }, [contestSearch, contestFilter]);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        try {
            const raw = window.localStorage.getItem(ADMIN_PREFERENCES_STORAGE_KEY);
            if (!raw) {
                return;
            }
            const parsed = JSON.parse(raw) as {
                tab?: AdminTab;
                contestFilter?: typeof contestFilter;
                actionFilter?: typeof actionFilter;
                contestSearch?: string;
                contestPage?: number;
                actionSearch?: string;
                growthDays?: number;
            };

            if (parsed.tab && ['dash', 'contests', 'archive', 'journal', 'channels'].includes(parsed.tab)) {
                setActiveTab(parsed.tab);
            }
            if (parsed.contestFilter && ['all', 'scheduled', 'active', 'draft', 'finished', 'results_published'].includes(parsed.contestFilter)) {
                setContestFilter(parsed.contestFilter);
            }
            if (parsed.actionFilter && ['all', 'contest', 'channel', 'youtube_channel', 'tiktok_channel'].includes(parsed.actionFilter)) {
                setActionFilter(parsed.actionFilter);
            }
            if (typeof parsed.contestSearch === 'string') {
                setContestSearch(parsed.contestSearch);
            }
            if (typeof parsed.contestPage === 'number' && parsed.contestPage > 0) {
                setContestPage(parsed.contestPage);
            }
            if (typeof parsed.actionSearch === 'string') {
                setActionSearch(parsed.actionSearch);
            }
            if (parsed.growthDays === 7 || parsed.growthDays === 30 || parsed.growthDays === 90) {
                setGrowthDays(parsed.growthDays);
            }
        } catch (storageError) {
            console.warn('Failed to restore admin preferences', storageError);
        }
    }, []);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }
        try {
            window.localStorage.setItem(
                ADMIN_PREFERENCES_STORAGE_KEY,
                JSON.stringify({
                    tab: activeTab,
                    contestFilter,
                    actionFilter,
                    contestSearch,
                    contestPage,
                    actionSearch,
                    growthDays,
                })
            );
        } catch (storageError) {
            console.warn('Failed to save admin preferences', storageError);
        }
    }, [activeTab, contestFilter, actionFilter, contestSearch, contestPage, actionSearch, growthDays]);

    const refreshContestDetails = async (contestId?: number) => {
        await queryClient.invalidateQueries({ queryKey: ['admin_contests'] });
        await queryClient.invalidateQueries({ queryKey: ['admin_contests_paged'] });
        await queryClient.invalidateQueries({ queryKey: ['contest_history', contestId, initData] });
        await queryClient.invalidateQueries({ queryKey: ['admin_analytics', initData] });
        await queryClient.invalidateQueries({ queryKey: ['admin_analytics_growth', initData] });
        await queryClient.invalidateQueries({ queryKey: ['admin_recent_actions', initData] });
        await queryClient.invalidateQueries({ queryKey: ['billing_status', initData] });
    };

    const { data: contests, isLoading: isContestsLoading, refetch: refetchContests } = useQuery<AdminContest[]>({
        queryKey: ['admin_contests', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/contests', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData && activeTab !== 'channels',
    });

    const { data: pagedContests, isLoading: isPagedContestsLoading, refetch: refetchPagedContests } = useQuery<PaginatedContestsResponse>({
        queryKey: ['admin_contests_paged', initData, contestSearch, contestFilter, contestPage],
        queryFn: async () => {
            const res = await axios.get('/api/admin/contests', {
                headers: { '_auth': initData },
                params: {
                    _auth: initData,
                    paginated: true,
                    limit: contestPageSize,
                    offset: (contestPage - 1) * contestPageSize,
                    status: contestFilter === 'all' ? undefined : contestFilter,
                    search: contestSearch.trim() || undefined,
                }
            });
            return res.data;
        },
        enabled: !!initData && activeTab === 'contests',
    });

    const scheduledContests = (contests || []).filter(contest => effectiveStatus(contest) === 'scheduled');
    const draftContests = (contests || []).filter(contest => effectiveStatus(contest) === 'draft');
    const activeContests = (contests || []).filter(contest => effectiveStatus(contest) === 'active');
    const archivedContests = (contests || []).filter((contest) => {
        const status = effectiveStatus(contest);
        return status === 'finished' || status === 'results_published';
    });
    const sortedContests = [...(contests || [])].sort((left, right) => {
        const priorityDiff = contestStatusPriority(left) - contestStatusPriority(right);
        if (priorityDiff !== 0) {
            return priorityDiff;
        }

        const leftDate = left.publish_at || left.end_date;
        const rightDate = right.publish_at || right.end_date;
        return new Date(leftDate).getTime() - new Date(rightDate).getTime();
    });
    const filteredContests = sortedContests.filter((contest) => {
        const statusMatches = contestFilter === 'all' || effectiveStatus(contest) === contestFilter;
        const searchValue = contestSearch.trim().toLowerCase();
        if (!searchValue) {
            return statusMatches;
        }

        const haystack = [
            contest.title,
            contest.channel?.channel_title || '',
            contest.channel?.channel_username || '',
        ].join(' ').toLowerCase();

        return statusMatches && haystack.includes(searchValue);
    });
    const contestsList = activeTab === 'contests'
        ? (pagedContests?.items || [])
        : filteredContests;
    const contestsTotal = activeTab === 'contests'
        ? (pagedContests?.total || 0)
        : filteredContests.length;
    const contestsTotalPages = Math.max(1, Math.ceil(contestsTotal / contestPageSize));
    const { data: channels, refetch: refetchChannels } = useQuery<AdminChannel[]>({
        queryKey: ['admin_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData && (activeTab === 'channels' || isCreating),
    });

    const { data: youtubeChannels, refetch: refetchYoutubeChannels } = useQuery<AdminYoutubeChannel[]>({
        queryKey: ['admin_youtube_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/youtube-channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData && (activeTab === 'channels' || isCreating),
    });

    const { data: tiktokChannels, refetch: refetchTikTokChannels } = useQuery<AdminTikTokChannel[]>({
        queryKey: ['admin_tiktok_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/tiktok-channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData && (activeTab === 'channels' || isCreating),
    });

    const { data: analytics, refetch: refetchAnalytics } = useQuery<AnalyticsOverview>({
        queryKey: ['admin_analytics', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/analytics/overview', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData && activeTab === 'dash'
    });

    const { data: analyticsGrowth, refetch: refetchGrowth } = useQuery<GrowthPoint[]>({
        queryKey: ['admin_analytics_growth', initData, growthDays],
        queryFn: async () => {
            const res = await axios.get('/api/admin/analytics/growth', {
                headers: { '_auth': initData },
                params: { _auth: initData, days: growthDays }
            });
            return res.data;
        },
        enabled: !!initData && activeTab === 'dash'
    });

    const { data: analyticsHealth, refetch: refetchHealth } = useQuery<AnalyticsHealth>({
        queryKey: ['admin_analytics_health', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/analytics/health', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData && activeTab === 'dash'
    });

    const { data: subscriptionStatus, refetch: refetchSubscriptionStatus } = useQuery<SubscriptionStatus>({
        queryKey: ['billing_status', initData],
        queryFn: async () => {
            const res = await axios.get('/api/billing/status', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData,
    });

    const { data: recentActions } = useQuery<AdminHistoryItem[]>({
        queryKey: ['admin_recent_actions', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/actions/recent', {
                headers: { '_auth': initData },
                params: { _auth: initData, limit: 25 }
            });
            return res.data;
        },
        enabled: !!initData && (activeTab === 'dash' || activeTab === 'journal'),
    });

    const filteredRecentActions = (recentActions || []).filter((entry) => {
        const targetMatches = actionFilter === 'all' || entry.target_type === actionFilter;
        const searchValue = actionSearch.trim().toLowerCase();
        if (!searchValue) {
            return targetMatches;
        }

        const haystack = [
            historyActionLabels[entry.action_type] || entry.action_type,
            entry.contest_title || '',
            entry.message || '',
            entry.target_type || '',
            entry.target_id || '',
            formatHistoryDetails(entry) || '',
        ].join(' ').toLowerCase();

        return targetMatches && haystack.includes(searchValue);
    });

    useEffect(() => {
        if (!selectedContest || !contests) {
            return;
        }

        const updatedContest = contests.find(contest => contest.id === selectedContest.id);
        if (!updatedContest) {
            setSelectedContest(null);
            return;
        }

        if (
            updatedContest.status !== selectedContest.status ||
            updatedContest.publish_at !== selectedContest.publish_at ||
            updatedContest.participants_count !== selectedContest.participants_count ||
            updatedContest.end_date !== selectedContest.end_date
        ) {
            setSelectedContest(updatedContest);
        }
    }, [contests, selectedContest]);

    const handleTabChange = (tab: AdminTab) => {
        hapticFeedback('light');
        setActiveTab(tab);
        setIsCreating(false);
        setSelectedContest(null);
        setError(null);
        setSuccessMessage(null);
    };

    const openContestsWithFilter = (filter: typeof contestFilter) => {
        handleTabChange('contests');
        setContestFilter(filter);
    };

    const handleCreateSuccess = async (createdContest?: CreatedContest) => {
        setIsCreating(false);
        setActiveTab('contests');
        setContestFilter('all');
        setContestSearch('');
        setContestPage(1);
        setSuccessMessage('Конкурс создан');
        await queryClient.invalidateQueries({ queryKey: ['admin_contests'] });
        await queryClient.invalidateQueries({ queryKey: ['admin_contests_paged'] });
        await queryClient.invalidateQueries({ queryKey: ['admin_analytics', initData] });
        await queryClient.invalidateQueries({ queryKey: ['admin_analytics_growth', initData] });
        await queryClient.invalidateQueries({ queryKey: ['admin_recent_actions', initData] });
        await queryClient.invalidateQueries({ queryKey: ['billing_status', initData] });

        const contestsResult = await queryClient.fetchQuery<AdminContest[]>({
            queryKey: ['admin_contests', initData],
            queryFn: async () => {
                const res = await axios.get('/api/admin/contests', {
                    headers: { '_auth': initData },
                    params: { _auth: initData }
                });
                return res.data;
            },
        });
        const created = createdContest
            ? contestsResult.find(contest => contest.id === createdContest.id)
            : undefined;
        if (created) {
            setSelectedContest(created);
        }
    };

    const handleRefreshAll = () => {
        hapticFeedback('medium');
        refetchContests();
        if (activeTab === 'contests') {
            refetchPagedContests();
        }
        refetchChannels();
        refetchYoutubeChannels();
        refetchTikTokChannels();
        refetchAnalytics();
        refetchGrowth();
        refetchHealth();
        refetchSubscriptionStatus();
        queryClient.invalidateQueries({ queryKey: ['admin_recent_actions', initData] });
        setIsSettingsOpen(false);
        hapticFeedback('heavy');
    };

    const handlePaykassaCheckout = async () => {
        if (!initData) return;
        setPaymentLoading('paykassa');
        setError(null);
        setSuccessMessage(null);
        hapticFeedback('medium');
        try {
            const res = await axios.post('/api/billing/paykassa/create', null, {
                headers: { '_auth': initData },
                params: { _auth: initData, plan_code: 'contest_pro' }
            });
            const checkoutUrl = res.data?.checkout_url;
            if (!checkoutUrl) {
                throw new Error('PayKassa не вернула ссылку на оплату');
            }
            openLink(checkoutUrl, { try_browser: 'chrome' });
            setSuccessMessage('Ссылка PayKassa открыта. После оплаты статус обновится автоматически.');
        } catch (err) {
            setError(extractErrorMessage(err, 'Не удалось создать счет PayKassa'));
            hapticFeedback('rigid');
        } finally {
            setPaymentLoading(null);
        }
    };

    const handleStarsSubscribe = () => {
        setPaymentLoading('stars');
        setError(null);
        setSuccessMessage('Для теста Telegram Stars отправь боту команду /subscribe pro');
        hapticFeedback('light');
        openTelegramLink('https://t.me/telonyx_contest_bot');
        window.setTimeout(() => setPaymentLoading(null), 600);
    };

    const handleOpenContestById = (contestId: number) => {
        const contest = (contests || []).find(item => item.id === contestId);
        if (!contest) {
            setError('Этот конкурс уже недоступен в текущем списке');
            setSuccessMessage(null);
            return;
        }

        setSelectedContest(contest);
        setError(null);
        setSuccessMessage(null);
    };

    const handlePublish = async (contestId: number) => {
        setActionLoadingKey(actionKey('publish', contestId));
        setError(null);
        setSuccessMessage(null);
        hapticFeedback('medium');
        try {
            await axios.post(`/api/publish/contest/${contestId}`, {}, {
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage('Конкурс опубликован');
            setSelectedContest(null);
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to publish', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Ошибка при публикации конкурса'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleSchedulePublish = async (contestId: number) => {
        if (!scheduleAt) return;
        setActionLoadingKey(actionKey('schedule', contestId));
        setError(null);
        setSuccessMessage(null);
        try {
            await axios.post(`/api/admin/contests/${contestId}/schedule-publish`, {
                publish_at: scheduleAt
            }, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage('Публикация запланирована');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to schedule publish', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось запланировать публикацию'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleCancelSchedulePublish = async (contestId: number) => {
        setActionLoadingKey(actionKey('cancelSchedule', contestId));
        setError(null);
        setSuccessMessage(null);
        try {
            await axios.post(`/api/admin/contests/${contestId}/cancel-schedule-publish`, {}, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage('Отложенная публикация отменена');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to cancel scheduled publish', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось отменить отложенную публикацию'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleRepublish = async (contestId: number, mode: 'repost' | 'edit') => {
        setActionLoadingKey(actionKey(mode === 'edit' ? 'editPost' : 'repost', contestId));
        setError(null);
        setSuccessMessage(null);
        try {
            await axios.post(`/api/admin/contests/${contestId}/republish`, { mode }, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage(mode === 'edit' ? 'Пост обновлен' : 'Конкурс перепубликован');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to republish contest', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось выполнить операцию перепубликации'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleExportParticipants = async (contestId: number) => {
        setError(null);
        setSuccessMessage(null);
        try {
            const response = await axios.get(`/api/admin/contests/${contestId}/participants/export`, {
                headers: { '_auth': initData },
                params: { _auth: initData },
                responseType: 'blob'
            });
            const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `contest_${contestId}_participants.csv`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            setSuccessMessage('CSV с участниками выгружен');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to export participants', err);
            setError(extractErrorMessage(err, 'Не удалось выгрузить участников'));
        }
    };

    const handleLoadPreview = async (contestId: number) => {
        setError(null);
        try {
            const res = await axios.get(`/api/admin/contests/${contestId}/preview`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            setPreview(res.data);
            setResultsPreview(null);
            setRepublishDiff(null);
        } catch (err: unknown) {
            setError(extractErrorMessage(err, 'Не удалось загрузить предпросмотр'));
        }
    };

    const handleLoadResultsPreview = async (contestId: number) => {
        setError(null);
        try {
            const res = await axios.get(`/api/admin/contests/${contestId}/results-preview`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            setResultsPreview(res.data);
            setPreview(null);
            setRepublishDiff(null);
        } catch (err: unknown) {
            setError(extractErrorMessage(err, 'Не удалось загрузить черновик результатов'));
        }
    };

    const handleLoadRepublishDiff = async (contestId: number) => {
        setError(null);
        try {
            const res = await axios.get(`/api/admin/contests/${contestId}/republish-diff`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            setRepublishDiff(res.data);
            setPreview(null);
            setResultsPreview(null);
        } catch (err: unknown) {
            setError(extractErrorMessage(err, 'Не удалось загрузить diff перепубликации'));
        }
    };

    const handlePublishResults = async (contestId: number) => {
        setActionLoadingKey(actionKey('publishResults', contestId));
        setError(null);
        setSuccessMessage(null);
        try {
            await axios.post(`/api/publish/results/${contestId}`, {}, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage('Результаты опубликованы');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to publish results', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось опубликовать результаты'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleRunContest = async (contestId: number) => {
        if (!confirm('Вы уверены, что хотите завершить конкурс и провести розыгрыш сейчас?')) return;
        setActionLoadingKey(actionKey('draw', contestId));
        hapticFeedback('medium');
        try {
            await axios.post(`/api/admin/contests/${contestId}/draw`, {}, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage('Розыгрыш проведен, проверьте черновик результатов');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to run contest', err);
            hapticFeedback('rigid');
            const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
            setError(detail || 'Ошибка при проведении розыгрыша');
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleDeleteContest = async (contestId: number) => {
        if (!confirm('Вы уверены, что хотите удалить этот конкурс? Это действие необратимо.')) return;
        setActionLoadingKey(actionKey('delete', contestId));
        hapticFeedback('medium');
        try {
            await axios.delete(`/api/admin/contests/${contestId}`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSelectedContest(null);
            setSuccessMessage('Конкурс удален');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to delete contest', err);
            hapticFeedback('rigid');
            const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
            setError(detail || 'Ошибка при удалении конкурса');
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleRepairContest = async (contestId: number) => {
        setActionLoadingKey(actionKey('repair', contestId));
        setError(null);
        setSuccessMessage(null);
        hapticFeedback('medium');
        try {
            const res = await axios.post(`/api/admin/contests/${contestId}/repair`, {}, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSuccessMessage(res.data?.message || 'Восстановление выполнено');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to repair contest', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось восстановить конкурс'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleDuplicateContest = async (contestId: number) => {
        setActionLoadingKey(actionKey('duplicate', contestId));
        setError(null);
        setSuccessMessage(null);
        hapticFeedback('medium');
        try {
            const response = await axios.post(`/api/admin/contests/${contestId}/duplicate`, {}, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            const duplicatedId = response.data?.contest?.id;
            setSuccessMessage(duplicatedId
                ? `Создана копия конкурса (ID: ${duplicatedId})`
                : 'Создана копия конкурса');
            setSelectedContest(null);
            openContestsWithFilter('draft');
            await refreshContestDetails(contestId);
        } catch (err: unknown) {
            console.error('Failed to duplicate contest', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось создать копию конкурса'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleBulkPublishNow = async () => {
        const ids = scheduledContests.map((contest) => contest.id);
        if (!ids.length) {
            setError('Нет запланированных конкурсов для публикации');
            return;
        }
        if (!confirm(`Опубликовать сейчас ${ids.length} запланированных конкурсов?`)) return;

        setActionLoadingKey(actionKey('bulkPublishScheduled'));
        setError(null);
        setSuccessMessage(null);
        hapticFeedback('medium');
        try {
            const res = await axios.post('/api/admin/contests/bulk/publish-now', {
                contest_ids: ids
            }, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            const publishedCount = Number(res.data?.published_count || 0);
            const skipped = Array.isArray(res.data?.skipped) ? res.data.skipped : [];
            const skippedCount = skipped.length;
            setSuccessMessage(
                `Массовая публикация: успешно ${publishedCount}, пропущено ${skippedCount} (${formatBulkSkippedSummary(skipped)})`
            );
            await refreshContestDetails();
        } catch (err: unknown) {
            console.error('Failed bulk publish', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось выполнить массовую публикацию'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleBulkCancelSchedule = async () => {
        const ids = scheduledContests.map((contest) => contest.id);
        if (!ids.length) {
            setError('Нет запланированных конкурсов для отмены');
            return;
        }
        if (!confirm(`Отменить отложенную публикацию для ${ids.length} конкурсов?`)) return;

        setActionLoadingKey(actionKey('bulkCancelSchedule'));
        setError(null);
        setSuccessMessage(null);
        hapticFeedback('medium');
        try {
            const res = await axios.post('/api/admin/contests/bulk/cancel-schedule', {
                contest_ids: ids
            }, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            const updatedCount = Number(res.data?.updated_count || 0);
            const skipped = Array.isArray(res.data?.skipped) ? res.data.skipped : [];
            const skippedCount = skipped.length;
            setSuccessMessage(
                `Отмена расписания: обновлено ${updatedCount}, пропущено ${skippedCount} (${formatBulkSkippedSummary(skipped)})`
            );
            await refreshContestDetails();
        } catch (err: unknown) {
            console.error('Failed bulk schedule cancel', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось выполнить массовую отмену'));
        } finally {
            setActionLoadingKey(null);
        }
    };

    const handleAddChannel = async () => {
        if (!newChannelInput) return;
        setIsAddingChannel(true);
        setError(null);
        hapticFeedback('medium');
        try {
            if (addingChannelType === 'telegram') {
                // 1. Resolve username and check admin status
                const resolveRes = await axios.get('/api/admin/channels/resolve-username', {
                    params: { username: newChannelInput.replace('@', ''), _auth: initData },
                    headers: { '_auth': initData }
                });

                const resolvedData = resolveRes.data;

                // 2. Create channel with resolved data
                await axios.post('/api/admin/channels', {
                    channel_id: resolvedData.channel_id,
                    channel_username: resolvedData.channel_username,
                    channel_title: resolvedData.channel_title
                }, {
                    headers: { '_auth': initData },
                    params: { _auth: initData }
                });
                await refetchChannels();
            } else if (addingChannelType === 'youtube') {
                // YouTube
                // Simple parsing for ID if full URL is given (very basic)
                let channelId = newChannelInput;
                if (channelId.includes('channel/')) {
                    channelId = channelId.split('channel/')[1].split('/')[0].split('?')[0];
                }

                await axios.post('/api/admin/youtube-channels', {
                    channel_id: channelId,
                    title: 'New YouTube Channel', // Placeholder, user can edit later or we can fetch
                    description: ''
                }, {
                    headers: { '_auth': initData },
                    params: { _auth: initData }
                });
                await refetchYoutubeChannels();
            } else if (addingChannelType === 'tiktok') {
                let channelId = newChannelInput.trim();
                channelId = channelId
                    .replace('https://www.tiktok.com/@', '')
                    .replace('https://tiktok.com/@', '')
                    .replace('https://www.tiktok.com/', '')
                    .replace('https://tiktok.com/', '')
                    .replace('www.tiktok.com/@', '')
                    .replace('tiktok.com/@', '')
                    .replace('www.tiktok.com/', '')
                    .replace('tiktok.com/', '')
                    .replace(/^@/, '')
                    .replace(/\/+$/, '')
                    .trim();

                await axios.post('/api/admin/tiktok-channels', {
                    channel_id: channelId,
                    title: `@${channelId}`,
                    description: ''
                }, {
                    headers: { '_auth': initData },
                    params: { _auth: initData }
                });
                await refetchTikTokChannels();
            }
            hapticFeedback('heavy');
            setAddingChannelType(null);
            setNewChannelInput('');
            setSuccessMessage(
                addingChannelType === 'telegram'
                    ? 'Telegram-канал добавлен'
                    : addingChannelType === 'youtube'
                        ? 'YouTube-канал добавлен'
                    : addingChannelType === 'tiktok'
                        ? 'TikTok-аккаунт добавлен'
                        : 'Канал добавлен'
            );
        } catch (err: unknown) {
            console.error('Failed to add channel', err);
            hapticFeedback('rigid');
            const res = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
            const detail = res?.data?.detail;
            if (res?.status === 403) {
                setError(detail || 'Бот должен быть администратором канала. Добавьте бота в канал и дайте права админа.');
            } else {
                setError(detail || 'Ошибка при добавлении канала');
            }
        } finally {
            setIsAddingChannel(false);
        }
    };

    const handleDeleteChannel = async (id: number) => {
        if (!confirm('Вы уверены, что хотите удалить этот канал?')) return;
        setError(null);
        try {
            await axios.delete(`/api/admin/channels/${id}`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            await refetchChannels();
            hapticFeedback('heavy');
            setSuccessMessage('Канал удален');
        } catch (err: unknown) {
            console.error('Failed to delete channel', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось удалить канал'));
        } finally {
            setActiveChannelId(null);
        }
    };

    const handleDeleteYoutubeChannel = async (channelId: string) => {
        if (!confirm('Вы уверены, что хотите удалить этот YouTube канал?')) return;
        setError(null);
        try {
            await axios.delete(`/api/admin/youtube-channels/${channelId}`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            await refetchYoutubeChannels();
            hapticFeedback('heavy');
            setSuccessMessage('YouTube-канал удален');
        } catch (err: unknown) {
            console.error('Failed to delete YouTube channel', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось удалить YouTube канал'));
        } finally {
            setActiveChannelId(null);
        }
    };

    const handleDeleteTikTokChannel = async (channelId: string) => {
        if (!confirm('Вы уверены, что хотите удалить этот TikTok аккаунт?')) return;
        setError(null);
        try {
            await axios.delete(`/api/admin/tiktok-channels/${channelId}`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            await refetchTikTokChannels();
            hapticFeedback('heavy');
            setSuccessMessage('TikTok-аккаунт удален');
        } catch (err: unknown) {
            console.error('Failed to delete TikTok channel', err);
            hapticFeedback('rigid');
            setError(extractErrorMessage(err, 'Не удалось удалить TikTok аккаунт'));
        } finally {
            setActiveChannelId(null);
        }
    };

    const handleUpdateChannel = async (channelId: number, username: string) => {
        hapticFeedback('medium');
        try {
            const resolveRes = await axios.get('/api/admin/channels/resolve-username', {
                params: { username: username.replace('@', ''), _auth: initData },
                headers: { '_auth': initData }
            });
            const resolvedData = resolveRes.data;

            await axios.put(`/api/admin/channels/${channelId}`, {
                ...resolvedData
            }, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            await refetchChannels();
            hapticFeedback('heavy');
            setSuccessMessage('Канал обновлен');
        } catch (err: unknown) {
            console.error('Failed to update channel', err);
            hapticFeedback('rigid');
            const res = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
            const detail = res?.data?.detail;
            if (res?.status === 403) {
                setError(detail || 'Бот должен быть администратором канала. Добавьте бота в канал и дайте права админа.');
            } else {
                setError(detail || 'Не удалось обновить данные канала');
            }
        } finally {
            setActiveChannelId(null);
        }
    };

    const { data: contestHistory } = useQuery<AdminHistoryItem[]>({
        queryKey: ['contest_history', selectedContest?.id, initData],
        queryFn: async () => {
            const res = await axios.get(`/api/admin/contests/${selectedContest?.id}/history`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!selectedContest?.id && !!initData,
    });

    return (
        <div className="space-y-6 pb-20">
            <AnimatePresence mode="wait">
                {isCreating ? (
                    <motion.div
                        key="create-form"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                    >
                        <Suspense fallback={<div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">Загрузка формы конкурса...</div>}>
                            <ContestForm
                                onSuccess={handleCreateSuccess}
                                onCancel={() => setIsCreating(false)}
                            />
                        </Suspense>
                    </motion.div>
                ) : selectedContest ? (
                    <motion.div
                        key="details"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className="space-y-6"
                    >
                        <header className="flex items-center space-x-3">
                            <button
                                onClick={() => setSelectedContest(null)}
                                className="p-2 bg-white/5 rounded-full text-white/40 active:scale-95 transition-all"
                            >
                                <ArrowLeft size={20} />
                            </button>
                            <h2 className="text-xl font-bold truncate">{selectedContest.title}</h2>
                        </header>

                        <div className="space-y-4">
                            {error && (
                                <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
                                    {error}
                                </div>
                            )}
                            {successMessage && (
                                <div className="text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3">
                                    {successMessage}
                                </div>
                            )}
                            <GlassCard className="p-5 space-y-4">
                                <div className="flex justify-between items-start">
                                    <div className={cn(
                                        'text-[8px] font-black tracking-widest px-2 py-1 rounded-md uppercase',
                                        effectiveStatus(selectedContest) === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                            effectiveStatus(selectedContest) === 'draft' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
                                                effectiveStatus(selectedContest) === 'scheduled' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                                                'bg-white/5 text-white/20 border border-white/10'
                                    )}>
                                        {effectiveStatus(selectedContest)}
                                    </div>
                                    <div className="text-[10px] text-white/40 font-bold uppercase tracking-wider">
                                        ID: {selectedContest.id}
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex items-center space-x-3">
                                        <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
                                            <Radio size={20} />
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-white/40 font-bold uppercase tracking-wider leading-none mb-1">Канал проведения</div>
                                            <div className="text-sm font-bold">{selectedContest.channel?.channel_title || 'Не указан'}</div>
                                        </div>
                                    </div>

                                    <div className="flex items-center space-x-3">
                                        <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center text-amber-500">
                                            <Trophy size={20} />
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-white/40 font-bold uppercase tracking-wider leading-none mb-1">Призовых мест</div>
                                            <div className="text-sm font-bold">{selectedContest.prize_count} / {selectedContest.prizes?.length || 0} настроено</div>
                                        </div>
                                    </div>

                                    <div className="flex items-center space-x-3">
                                        <div className="w-10 h-10 bg-emerald-500/10 rounded-xl flex items-center justify-center text-emerald-500">
                                            <Clock size={20} />
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-white/40 font-bold uppercase tracking-wider leading-none mb-1">Дата окончания</div>
                                            <div className="text-sm font-bold">{new Date(selectedContest.end_date).toLocaleString()}</div>
                                        </div>
                                    </div>

                                    {selectedContest.publish_at && (
                                        <div className="flex items-center space-x-3">
                                            <div className="w-10 h-10 bg-sky-500/10 rounded-xl flex items-center justify-center text-sky-400">
                                                <Clock size={20} />
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-white/40 font-bold uppercase tracking-wider leading-none mb-1">Публикация</div>
                                                <div className="text-sm font-bold">{new Date(selectedContest.publish_at).toLocaleString()}</div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {selectedContest.require_youtube_subscription && (
                                    <div className="pt-4 border-t border-white/5">
                                        <div className="flex items-center space-x-2 text-red-400">
                                            <Youtube size={14} />
                                            <span className="text-[10px] font-bold uppercase tracking-wider">Требуется YouTube ({selectedContest.youtube_subscription_days_required} дн.)</span>
                                        </div>
                                    </div>
                                )}
                                {selectedContest.require_tiktok_follow && (
                                    <div className="pt-2">
                                        <div className="flex items-center space-x-2 text-violet-400">
                                            <AlertCircle size={14} />
                                            <span className="text-[10px] font-bold uppercase tracking-wider">Требуется TikTok</span>
                                        </div>
                                    </div>
                                )}
                                {selectedContest.require_captcha && (
                                    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-3 text-cyan-200">
                                        <div className="flex items-center gap-2">
                                            <AlertCircle size={16} />
                                            <span className="text-[10px] font-bold uppercase tracking-wider">Требуется капча</span>
                                        </div>
                                    </div>
                                )}
                            </GlassCard>

                            <Button
                                variant="secondary"
                                onClick={() => handleDuplicateContest(selectedContest.id)}
                                isLoading={isActionLoading('duplicate', selectedContest.id)}
                                className="w-full"
                            >
                                СОЗДАТЬ КОПИЮ КАК ЧЕРНОВИК
                            </Button>

                            {effectiveStatus(selectedContest) === 'draft' && (
                                <div className="space-y-3">
                                    <Button
                                        variant="secondary"
                                        onClick={() => handleLoadPreview(selectedContest.id)}
                                        className="w-full"
                                    >
                                        ПРЕДПРОСМОТР ПОСТА
                                    </Button>
                                    <Button
                                        onClick={() => handlePublish(selectedContest.id)}
                                        isLoading={isActionLoading('publish', selectedContest.id)}
                                        className="w-full bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20"
                                    >
                                        <Send size={18} className="mr-2" /> ОПУБЛИКОВАТЬ В КАНАЛ
                                    </Button>
                                    <div className="space-y-2">
                                        <input
                                            type="datetime-local"
                                            className="form-input"
                                            value={scheduleAt}
                                            onChange={e => setScheduleAt(e.target.value)}
                                        />
                                        <Button
                                            variant="secondary"
                                            onClick={() => handleSchedulePublish(selectedContest.id)}
                                            isLoading={isActionLoading('schedule', selectedContest.id)}
                                            disabled={!scheduleAt}
                                            className="w-full"
                                        >
                                            ЗАПЛАНИРОВАТЬ ПУБЛИКАЦИЮ
                                        </Button>
                                    </div>
                                    <p className="text-[10px] text-center text-white/40 italic px-4">
                                        Конкурс будет немедленно опубликован в выбранном Telegram канале и станет доступен для регистрации.
                                    </p>
                                </div>
                            )}

                            {effectiveStatus(selectedContest) === 'scheduled' && (
                                <div className="space-y-3">
                                    <div className="p-4 bg-sky-500/10 border border-sky-500/20 rounded-2xl flex items-center space-x-3 text-sky-300">
                                        <Clock size={24} />
                                        <div className="text-sm font-bold">Конкурс запланирован к публикации</div>
                                    </div>
                                    <Button
                                        variant="secondary"
                                        onClick={() => handleLoadPreview(selectedContest.id)}
                                        className="w-full"
                                    >
                                        ПРЕДПРОСМОТР ПОСТА
                                    </Button>
                                    <Button
                                        onClick={() => handlePublish(selectedContest.id)}
                                        isLoading={isActionLoading('publish', selectedContest.id)}
                                        className="w-full bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20"
                                    >
                                        ОПУБЛИКОВАТЬ СЕЙЧАС
                                    </Button>
                                    <Button
                                        variant="secondary"
                                        onClick={() => handleCancelSchedulePublish(selectedContest.id)}
                                        isLoading={isActionLoading('cancelSchedule', selectedContest.id)}
                                        className="w-full"
                                    >
                                        ОТМЕНИТЬ ОТЛОЖЕННУЮ ПУБЛИКАЦИЮ
                                    </Button>
                                </div>
                            )}

                                    {effectiveStatus(selectedContest) === 'active' && (
                                        <div className="space-y-3">
                                            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center space-x-3 text-emerald-400">
                                                <CheckCircle2 size={24} />
                                                <div className="text-sm font-bold">Конкурс запущен и активен</div>
                                            </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <Button variant="secondary" onClick={() => handleLoadPreview(selectedContest.id)} className="w-full">
                                            ПРЕДПРОСМОТР
                                        </Button>
                                        <Button variant="secondary" onClick={() => handleExportParticipants(selectedContest.id)} className="w-full">
                                            ЭКСПОРТ CSV
                                        </Button>
                                    </div>
                                            <Button
                                                variant="secondary"
                                                onClick={() => handleRepairContest(selectedContest.id)}
                                                isLoading={isActionLoading('repair', selectedContest.id)}
                                                className="w-full"
                                            >
                                                ВОССТАНОВИТЬ КОНКУРС
                                            </Button>
                                            <div className="grid grid-cols-2 gap-3">
                                                <Button
                                                    variant="secondary"
                                                    onClick={() => handleLoadRepublishDiff(selectedContest.id)}
                                                    className="w-full col-span-2"
                                                >
                                                    ПОКАЗАТЬ DIFF ПЕРЕД ПЕРЕПУБЛИКАЦИЕЙ
                                                </Button>
                                                <Button
                                                    variant="secondary"
                                                    onClick={() => handleRepublish(selectedContest.id, 'edit')}
                                                    isLoading={isActionLoading('editPost', selectedContest.id)}
                                                    className="w-full"
                                                >
                                                    ОБНОВИТЬ ПОСТ
                                                </Button>
                                                <Button
                                                    variant="secondary"
                                                    onClick={() => handleRepublish(selectedContest.id, 'repost')}
                                                    isLoading={isActionLoading('repost', selectedContest.id)}
                                                    className="w-full"
                                                >
                                                    ПЕРЕПУБЛИКОВАТЬ
                                                </Button>
                                            </div>
                                            <Button
                                                onClick={() => handleRunContest(selectedContest.id)}
                                                isLoading={isActionLoading('draw', selectedContest.id)}
                                                className="w-full bg-amber-500 hover:bg-amber-600 text-white shadow-lg shadow-amber-500/20"
                                            >
                                                <Trophy size={18} className="mr-2" /> РАЗЫГРАТЬ СЕЙЧАС
                                            </Button>
                                            <Button
                                                variant="secondary"
                                                onClick={() => handleDeleteContest(selectedContest.id)}
                                                isLoading={isActionLoading('delete', selectedContest.id)}
                                                className="w-full text-red-500/60 border-red-500/10 hover:bg-red-500/10"
                                            >
                                                <Trash2 size={18} className="mr-2" /> УДАЛИТЬ КОНКУРС
                                            </Button>
                                        </div>
                                    )}

                            {effectiveStatus(selectedContest) === 'finished' && (
                                <div className="space-y-3">
                                    <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-center space-x-3 text-amber-300">
                                        <Trophy size={24} />
                                        <div className="text-sm font-bold">Розыгрыш завершен, результаты готовы к проверке</div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <Button variant="secondary" onClick={() => handleLoadResultsPreview(selectedContest.id)} className="w-full">
                                            ЧЕРНОВИК РЕЗУЛЬТАТОВ
                                        </Button>
                                        <Button variant="secondary" onClick={() => handleExportParticipants(selectedContest.id)} className="w-full">
                                            ЭКСПОРТ CSV
                                        </Button>
                                    </div>
                                    <Button
                                        variant="secondary"
                                        onClick={() => handleRepairContest(selectedContest.id)}
                                        isLoading={isActionLoading('repair', selectedContest.id)}
                                        className="w-full"
                                    >
                                        ВОССТАНОВИТЬ КОНКУРС
                                    </Button>
                                    <Button
                                        onClick={() => handlePublishResults(selectedContest.id)}
                                        isLoading={isActionLoading('publishResults', selectedContest.id)}
                                        className="w-full bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20"
                                    >
                                        ОПУБЛИКОВАТЬ РЕЗУЛЬТАТЫ
                                    </Button>
                                </div>
                            )}

                            {effectiveStatus(selectedContest) === 'results_published' && (
                                <div className="space-y-3">
                                    <div className="p-4 bg-white/5 border border-white/10 rounded-2xl flex items-center space-x-3 text-white/70">
                                        <CheckCircle2 size={24} />
                                        <div className="text-sm font-bold">Результаты уже опубликованы</div>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <Button variant="secondary" onClick={() => handleLoadResultsPreview(selectedContest.id)} className="w-full">
                                            ПРЕДПРОСМОТР РЕЗУЛЬТАТОВ
                                        </Button>
                                        <Button variant="secondary" onClick={() => handleExportParticipants(selectedContest.id)} className="w-full">
                                            ЭКСПОРТ CSV
                                        </Button>
                                    </div>
                                    <Button
                                        variant="secondary"
                                        onClick={() => handleRepairContest(selectedContest.id)}
                                        isLoading={isActionLoading('repair', selectedContest.id)}
                                        className="w-full"
                                    >
                                        ВОССТАНОВИТЬ КОНКУРС
                                    </Button>
                                </div>
                            )}

                            {effectiveStatus(selectedContest) !== 'active' && (
                                <Button
                                    variant="secondary"
                                    onClick={() => handleDeleteContest(selectedContest.id)}
                                    isLoading={isActionLoading('delete', selectedContest.id)}
                                    className="w-full text-red-500/70 border-red-500/10 hover:bg-red-500/10"
                                >
                                    <Trash2 size={18} className="mr-2" /> УДАЛИТЬ КОНКУРС
                                </Button>
                            )}

                            {preview && preview.contest_id === selectedContest.id && (
                                <GlassCard className="p-4 space-y-3">
                                    <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Предпросмотр публикации</div>
                                    <div className="text-xs whitespace-pre-wrap leading-6 text-white/80">{preview.text}</div>
                                    {preview.button_url && (
                                        <div className="text-[11px] text-primary break-all">{preview.button_url}</div>
                                    )}
                                </GlassCard>
                            )}

                            {resultsPreview && resultsPreview.contest_id === selectedContest.id && (
                                <GlassCard className="p-4 space-y-3">
                                    <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Черновик результатов</div>
                                    <div className="text-xs whitespace-pre-wrap leading-6 text-white/80">{resultsPreview.text}</div>
                                    <div className="space-y-2">
                                        {resultsPreview.winners.map((winner) => (
                                            <div key={winner.place} className="text-xs text-white/70">
                                                {winner.place} место: {winner.title} - {winner.winner_username || winner.winner_firstname || winner.winner_user_id}
                                            </div>
                                        ))}
                                    </div>
                                </GlassCard>
                            )}

                            {republishDiff && republishDiff.contest_id === selectedContest.id && (
                                <GlassCard className="p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Diff перепубликации</div>
                                        <div className={cn(
                                            "text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md",
                                            republishDiff.has_changes
                                                ? "text-amber-300 bg-amber-500/10"
                                                : "text-emerald-300 bg-emerald-500/10"
                                        )}>
                                            {republishDiff.has_changes ? 'Есть изменения' : 'Без изменений'}
                                        </div>
                                    </div>
                                    {republishDiff.diff ? (
                                        <pre className="text-[11px] whitespace-pre-wrap leading-5 text-white/75 bg-black/20 border border-white/10 rounded-xl p-3 overflow-auto">
                                            {republishDiff.diff}
                                        </pre>
                                    ) : (
                                        <div className="text-xs text-white/45">Diff пуст, текущий и предыдущий рендер совпадают.</div>
                                    )}
                                    {!republishDiff.has_baseline && (
                                        <div className="text-[11px] text-white/45">
                                            Базовый рендер не найден в истории публикаций. Показано сравнение с пустым шаблоном.
                                        </div>
                                    )}
                                    {republishDiff.button_url && (
                                        <div className="text-[11px] text-primary break-all">{republishDiff.button_url}</div>
                                    )}
                                </GlassCard>
                            )}

                            {contestHistory && (
                                <GlassCard className="p-4 space-y-3">
                                    <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">История действий</div>
                                    {contestHistory.length > 0 ? (
                                        <div className="space-y-2">
                                            {contestHistory.slice(0, 8).map((entry) => (
                                                <div key={entry.id} className="text-xs text-white/70 flex items-start justify-between gap-4">
                                                    <div className="min-w-0">
                                                        <div className="font-semibold text-white/85">
                                                            {historyActionLabels[entry.action_type] || entry.action_type}
                                                        </div>
                                                        {formatHistoryDetails(entry) && (
                                                            <div className="text-white/40">{formatHistoryDetails(entry)}</div>
                                                        )}
                                                    </div>
                                                    <div className="shrink-0 text-white/30">
                                                        {new Date(entry.created_at).toLocaleString()}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-xs text-white/40">
                                            Действий по этому конкурсу пока нет.
                                        </div>
                                    )}
                                </GlassCard>
                            )}
                        </div>
                    </motion.div>
                ) : (
                    <motion.div
                        key="dashboard"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="space-y-6"
                    >
                        {(error || successMessage) && (
                            <div className={cn(
                                "text-xs rounded-xl px-4 py-3 border",
                                error ? "text-red-300 bg-red-500/10 border-red-500/20" : "text-emerald-300 bg-emerald-500/10 border-emerald-500/20"
                            )}>
                                {error || successMessage}
                            </div>
                        )}
                        <header className="flex items-center justify-between px-1 relative z-20">
                            <h1 className="text-2xl font-black italic tracking-tighter">ADMIN <span className="text-primary">PANEL</span></h1>
                            <div className="relative">
                                <Button
                                    variant="secondary"
                                    className="p-2 w-10 h-10 rounded-full"
                                    onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                                >
                                    <Settings size={18} />
                                </Button>
                                <AnimatePresence>
                                    {isSettingsOpen && (
                                        <motion.div
                                            initial={{ opacity: 0, scale: 0.9, y: 10 }}
                                            animate={{ opacity: 1, scale: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.9, y: 10 }}
                                            className="absolute right-0 top-12 w-48 bg-[#1c1c1e] border border-white/10 rounded-xl shadow-2xl overflow-hidden"
                                        >
                                            <div className="p-1 space-y-1">
                                                <button
                                                    onClick={handleRefreshAll}
                                                    className="w-full flex items-center space-x-2 px-3 py-2 text-xs font-bold text-white/80 hover:bg-white/5 rounded-lg transition-colors"
                                                >
                                                    <RefreshCw size={14} />
                                                    <span>Обновить данные</span>
                                                </button>
                                                <div className="px-3 py-2 text-[10px] text-white/30 border-t border-white/5 text-center">
                                                    Версия 2.0.0 (Beta)
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        </header>

                        {/* Stats Quick Grid */}
                        <Suspense fallback={<div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">Загрузка статистики...</div>}>
                            <DashboardStatsGrid
                                totalContests={analytics?.total_contests || 0}
                                activeContests={analytics?.active_contests || 0}
                                completedContests={analytics?.completed_contests || 0}
                                scheduledCount={scheduledContests.length}
                                draftCount={draftContests.length}
                                archivedCount={archivedContests.length}
                                onOpenAllContests={() => openContestsWithFilter('all')}
                                onOpenActiveContests={() => openContestsWithFilter('active')}
                                onOpenScheduledContests={() => openContestsWithFilter('scheduled')}
                                onOpenDraftContests={() => openContestsWithFilter('draft')}
                                onOpenArchive={() => handleTabChange('archive')}
                            />
                        </Suspense>

                        {/* Tabs */}
                        <div className="flex bg-white/5 p-1 rounded-xl border border-white/5">
                            {[
                                { id: 'dash', label: 'Обзор' },
                                { id: 'contests', label: 'Конкурсы' },
                                { id: 'archive', label: 'Архив' },
                                { id: 'journal', label: 'Журнал' },
                                { id: 'channels', label: 'Каналы' }
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => handleTabChange(tab.id as AdminTab)}
                                    className={cn(
                                        'flex-1 py-2.5 text-[10px] uppercase tracking-widest font-black rounded-lg transition-all',
                                        activeTab === tab.id ? 'bg-primary text-white shadow-lg' : 'text-white/40'
                                    )}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        <AnimatePresence mode="wait">
                            {activeTab === 'dash' && (
                                <motion.div
                                    key="dash"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="space-y-4"
                                >
                                    {subscriptionStatus && (
                                        <GlassCard className="p-4 border-white/5 space-y-3">
                                            <div className="flex items-start justify-between gap-3">
                                                <div>
                                                    <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Подписка</h3>
                                                    <div className="mt-1 text-sm font-black text-white/90">{subscriptionStatus.plan.title}</div>
                                                    <div className="text-[11px] text-white/40">
                                                        {subscriptionStatus.subscription?.ends_at
                                                            ? `Активна до ${new Date(subscriptionStatus.subscription.ends_at).toLocaleDateString()}`
                                                            : subscriptionStatus.is_super_admin
                                                                ? 'Админ-доступ без оплаченной подписки'
                                                                : 'Активная подписка не найдена'}
                                                    </div>
                                                </div>
                                                <div className={cn(
                                                    'rounded-xl px-3 py-2 text-[10px] font-black uppercase tracking-wider',
                                                    subscriptionStatus.active
                                                        ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                                                        : 'bg-red-500/10 text-red-300 border border-red-500/20'
                                                )}>
                                                    {subscriptionStatus.is_super_admin && !subscriptionStatus.subscription ? 'Admin' : subscriptionStatus.active ? 'Active' : 'Paused'}
                                                </div>
                                            </div>
                                            {!subscriptionStatus.subscription && (
                                                <div className="rounded-2xl border border-white/5 bg-white/[0.025] p-3 space-y-3">
                                                    <div>
                                                        <div className="text-xs font-bold text-white/80">Тест оплаты подписки</div>
                                                        <div className="mt-1 text-[11px] leading-relaxed text-white/40">
                                                            PayKassa откроет счет прямо из мини-аппа. Telegram Stars тестируются через инвойс в личке бота.
                                                        </div>
                                                    </div>
                                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                        <Button
                                                            type="button"
                                                            onClick={handlePaykassaCheckout}
                                                            isLoading={paymentLoading === 'paykassa'}
                                                            disabled={paymentLoading !== null}
                                                            className="w-full"
                                                        >
                                                            Купить через PayKassa
                                                        </Button>
                                                        <Button
                                                            type="button"
                                                            variant="secondary"
                                                            onClick={handleStarsSubscribe}
                                                            isLoading={paymentLoading === 'stars'}
                                                            disabled={paymentLoading !== null}
                                                            className="w-full"
                                                        >
                                                            Telegram Stars
                                                        </Button>
                                                    </div>
                                                </div>
                                            )}
                                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                                {[
                                                    ['Каналы', subscriptionStatus.usage.channels, subscriptionStatus.plan.limits.max_channels],
                                                    ['Активные', subscriptionStatus.usage.active_contests, subscriptionStatus.plan.limits.max_active_contests],
                                                    ['Черновики', subscriptionStatus.usage.draft_contests, subscriptionStatus.plan.limits.max_draft_contests],
                                                    [
                                                        'Соцсети',
                                                        Math.max(
                                                            subscriptionStatus.usage.youtube_channels,
                                                            subscriptionStatus.usage.tiktok_channels
                                                        ),
                                                        subscriptionStatus.plan.limits.max_external_channels_per_platform
                                                    ],
                                                ].map(([label, used, limit]) => (
                                                    <div key={String(label)} className="rounded-2xl bg-white/[0.03] border border-white/5 p-3">
                                                        <div className="text-[10px] uppercase tracking-wider text-white/35">{label}</div>
                                                        <div className="mt-1 text-lg font-black text-white">{used}<span className="text-xs text-white/35">/{limit}</span></div>
                                                    </div>
                                                ))}
                                            </div>
                                        </GlassCard>
                                    )}

                                    <GlassCard className="p-4 border-white/5 space-y-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Рост аудитории</h3>
                                                <div className="hidden sm:flex items-center gap-1">
                                                    {[7, 30, 90].map((period) => (
                                                        <button
                                                            key={period}
                                                            onClick={() => setGrowthDays(period as 7 | 30 | 90)}
                                                            className={cn(
                                                                'px-2 py-1 rounded-md text-[10px] font-bold transition-colors',
                                                                growthDays === period
                                                                    ? 'bg-primary text-white'
                                                                    : 'bg-white/5 text-white/45 hover:bg-white/10'
                                                            )}
                                                        >
                                                            {period}д
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="text-xs font-bold text-primary flex items-center bg-primary/10 px-2 py-1 rounded-md">
                                                <Users size={12} className="mr-1" />
                                                {analytics?.total_participants || 0}
                                            </div>
                                        </div>
                                        <div className="sm:hidden flex items-center gap-1">
                                            {[7, 30, 90].map((period) => (
                                                <button
                                                    key={period}
                                                    onClick={() => setGrowthDays(period as 7 | 30 | 90)}
                                                    className={cn(
                                                        'px-2 py-1 rounded-md text-[10px] font-bold transition-colors',
                                                        growthDays === period
                                                            ? 'bg-primary text-white'
                                                            : 'bg-white/5 text-white/45 hover:bg-white/10'
                                                    )}
                                                >
                                                    {period} дней
                                                </button>
                                            ))}
                                        </div>
                                        <Suspense fallback={<div className="h-48 w-full rounded-2xl bg-white/5 animate-pulse" />}>
                                            <GrowthChart data={analyticsGrowth} />
                                        </Suspense>
                                    </GlassCard>

                                    <GlassCard className="p-4 border-white/5 space-y-4">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Запланированные публикации</h3>
                                            <div className="text-[10px] text-white/30">
                                                {scheduledContests.length > 0 ? `${scheduledContests.length} в очереди` : 'Очередь пуста'}
                                            </div>
                                        </div>
                                        {scheduledContests.length > 0 ? (
                                            <div className="space-y-3">
                                                {scheduledContests.slice(0, 5).map((contest) => (
                                                    <div
                                                        key={contest.id}
                                                        className="w-full text-left p-3 rounded-2xl border border-sky-500/10 bg-sky-500/5 hover:bg-sky-500/10 transition-colors"
                                                    >
                                                        <div className="flex items-start justify-between gap-3">
                                                            <div className="min-w-0">
                                                                <div className="font-semibold text-sm text-white/90 truncate">{contest.title}</div>
                                                                <div className="text-[11px] text-white/45 truncate">
                                                                    {contest.channel?.channel_title || 'Без канала'}
                                                                </div>
                                                            </div>
                                                            <div className="text-[10px] text-sky-300 shrink-0">
                                                                {contest.publish_at ? new Date(contest.publish_at).toLocaleString() : 'Без даты'}
                                                            </div>
                                                        </div>
                                                        <div className="grid grid-cols-3 gap-2 mt-3">
                                                            <button
                                                                onClick={() => handleOpenContestById(contest.id)}
                                                                className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-[10px] font-bold uppercase tracking-wider text-white/70 transition-colors"
                                                            >
                                                                Открыть
                                                            </button>
                                                            <button
                                                                onClick={() => handlePublish(contest.id)}
                                                                disabled={!!actionLoadingKey}
                                                                className="px-3 py-2 rounded-xl bg-primary/15 hover:bg-primary/20 text-[10px] font-bold uppercase tracking-wider text-primary transition-colors disabled:opacity-50"
                                                            >
                                                                {isActionLoading('publish', contest.id) ? '...' : 'Сейчас'}
                                                            </button>
                                                            <button
                                                                onClick={() => handleCancelSchedulePublish(contest.id)}
                                                                disabled={!!actionLoadingKey}
                                                                className="px-3 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/15 text-[10px] font-bold uppercase tracking-wider text-red-300 transition-colors disabled:opacity-50"
                                                            >
                                                                {isActionLoading('cancelSchedule', contest.id) ? '...' : 'Отменить'}
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                                <div className="grid grid-cols-2 gap-2">
                                                    <Button
                                                        variant="secondary"
                                                        onClick={handleBulkPublishNow}
                                                        isLoading={isActionLoading('bulkPublishScheduled')}
                                                        className="w-full"
                                                    >
                                                        ОПУБЛИКОВАТЬ ВСЕ
                                                    </Button>
                                                    <Button
                                                        variant="secondary"
                                                        onClick={handleBulkCancelSchedule}
                                                        isLoading={isActionLoading('bulkCancelSchedule')}
                                                        className="w-full"
                                                    >
                                                        ОТМЕНИТЬ ВСЕ
                                                    </Button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="text-xs text-white/40">
                                                Нет конкурсов, ожидающих публикации. Активных сейчас: {activeContests.length}, черновиков: {draftContests.length}.
                                            </div>
                                        )}
                                    </GlassCard>

                                    <Suspense fallback={<div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">Загрузка состояния системы...</div>}>
                                        <SystemHealthPanel health={analyticsHealth} onOpenContest={handleOpenContestById} />
                                    </Suspense>

                                    <Suspense fallback={<div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">Загрузка панели...</div>}>
                                        <DashboardQuickPanels
                                            recentActionsCount={recentActions?.length || 0}
                                            archivedContestsCount={archivedContests.length}
                                            onOpenJournal={() => handleTabChange('journal')}
                                            onOpenArchive={() => handleTabChange('archive')}
                                        />
                                    </Suspense>
                                </motion.div>
                            )}
                            {activeTab === 'contests' && (
                                <motion.div
                                    key="contests"
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="space-y-4"
                                >
                                    <div className="flex items-center justify-between px-1">
                                        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Ваши розыгрыши</h3>
                                        <button
                                            onClick={() => setIsCreating(true)}
                                            className="text-[10px] font-black uppercase text-primary bg-primary/10 px-3 py-1.5 rounded-lg flex items-center space-x-1 active:scale-95 transition-all"
                                        >
                                            <Plus size={14} />
                                            <span>Создать</span>
                                        </button>
                                    </div>

                                    <GlassCard className="p-4 border-white/5 space-y-3">
                                        <div className="grid grid-cols-1 gap-3">
                                            <input
                                                type="text"
                                                value={contestSearch}
                                                onChange={(e) => setContestSearch(e.target.value)}
                                                placeholder="Поиск по названию или каналу"
                                                className="form-input"
                                            />
                                            <div className="flex flex-wrap gap-2">
                                                {[
                                                    { id: 'all', label: 'Все' },
                                                    { id: 'scheduled', label: 'Заплан.' },
                                                    { id: 'active', label: 'Активные' },
                                                    { id: 'draft', label: 'Черновики' },
                                                    { id: 'finished', label: 'Завершённые' },
                                                    { id: 'results_published', label: 'С результатами' },
                                                ].map((filter) => (
                                                    <button
                                                        key={filter.id}
                                                        onClick={() => setContestFilter(filter.id as typeof contestFilter)}
                                                        className={cn(
                                                            'px-3 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-colors',
                                                            contestFilter === filter.id
                                                                ? 'bg-primary text-white'
                                                                : 'bg-white/5 text-white/55 hover:bg-white/10'
                                                        )}
                                                    >
                                                        {filter.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </GlassCard>

                                    <div className="space-y-3">
                                        {(isContestsLoading || (activeTab === 'contests' && isPagedContestsLoading)) ? (
                                            Array.from({ length: 3 }).map((_, i) => (
                                                <GlassCard key={i} className="p-4 border-white/5 space-y-4 animate-pulse">
                                                    <div className="flex justify-between">
                                                        <div className="space-y-2 w-2/3">
                                                            <div className="h-4 bg-white/10 rounded w-3/4"></div>
                                                            <div className="h-3 bg-white/5 rounded w-1/2"></div>
                                                        </div>
                                                        <div className="h-6 w-16 bg-white/5 rounded"></div>
                                                    </div>
                                                </GlassCard>
                                            ))
                                        ) : (
                                            <motion.div
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                className="space-y-3"
                                            >
                                                {contestsList.map((c) => (
                                                    <GlassCard
                                                        key={c.id}
                                                        onClick={() => setSelectedContest(c)}
                                                        className="p-4 hover:border-white/20 transition-all border-white/5 cursor-pointer active:scale-[0.98]"
                                                    >
                                                        <div className="flex justify-between items-start mb-4">
                                                            <div className="space-y-1">
                                                                <h4 className="font-bold text-base leading-tight">{c.title}</h4>
                                                                <div className="flex items-center space-x-2 text-white/40">
                                                                    <Radio size={10} className="text-primary" />
                                                                    <span className="text-[10px] uppercase font-bold tracking-wider">{c.channel?.channel_title || 'Нет канала'}</span>
                                                                </div>
                                                            </div>
                                                            <div className={cn(
                                                                'text-[8px] font-black tracking-widest px-2 py-1 rounded-md uppercase',
                                                                effectiveStatus(c) === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                                    effectiveStatus(c) === 'draft' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
                                                                        effectiveStatus(c) === 'scheduled' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                                                                        'bg-white/5 text-white/20 border border-white/10'
                                                            )}>
                                                                {effectiveStatus(c)}
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center justify-between pt-4 border-t border-white/5">
                                                            <div className="flex items-center space-x-4">
                                                                <div className="flex items-center space-x-1.5 text-white/40">
                                                                    <Users size={12} className="text-primary" />
                                                                    <span className="text-[10px] font-bold">{c.participants_count || 0}</span>
                                                                </div>
                                                                <div className="flex items-center space-x-1.5 text-white/40">
                                                                    <Trophy size={12} className="text-amber-400" />
                                                                    <span className="text-[10px] font-bold">{c.prize_count || 0}</span>
                                                                </div>
                                                            </div>
                                                            <div className="p-1 px-2 rounded-lg bg-white/5 text-white/20">
                                                                <ChevronRight size={14} />
                                                            </div>
                                                        </div>
                                                    </GlassCard>
                                                ))}
                                                {contestsList.length === 0 && (
                                                    <div className="py-20 text-center space-y-4">
                                                        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto text-white/10">
                                                            <Trophy size={32} />
                                                        </div>
                                                        <p className="text-sm text-white/20 italic">
                                                            {contestsTotal > 0 ? 'По текущему фильтру конкурсы не найдены' : 'Конкурсов пока нет'}
                                                        </p>
                                                        {contestsTotal === 0 && <Button variant="secondary" onClick={() => setIsCreating(true)}>Создать первый</Button>}
                                                    </div>
                                                )}

                                                {contestsTotal > 0 && (
                                                    <GlassCard className="p-3 border-white/5">
                                                        <div className="flex items-center justify-between">
                                                            <div className="text-[11px] text-white/45">
                                                                Показано {Math.min((contestPage - 1) * contestPageSize + 1, contestsTotal)}-
                                                                {Math.min(contestPage * contestPageSize, contestsTotal)} из {contestsTotal}
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                <button
                                                                    onClick={() => setContestPage((page) => Math.max(1, page - 1))}
                                                                    disabled={contestPage <= 1}
                                                                    className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-[10px] font-bold uppercase tracking-wider text-white/70 transition-colors disabled:opacity-40"
                                                                >
                                                                    Назад
                                                                </button>
                                                                <div className="text-[10px] text-white/45">
                                                                    {contestPage}/{contestsTotalPages}
                                                                </div>
                                                                <button
                                                                    onClick={() => setContestPage((page) => Math.min(contestsTotalPages, page + 1))}
                                                                    disabled={contestPage >= contestsTotalPages}
                                                                    className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-[10px] font-bold uppercase tracking-wider text-white/70 transition-colors disabled:opacity-40"
                                                                >
                                                                    Вперёд
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </GlassCard>
                                                )}
                                            </motion.div>
                                        )}
                                    </div>
                                </motion.div>
                            )}

                            {activeTab === 'archive' && (
                                <Suspense fallback={<div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">Загрузка архива...</div>}>
                                    <ArchiveTab
                                        archivedContests={archivedContests}
                                        effectiveStatus={effectiveStatus}
                                        onOpenContest={handleOpenContestById}
                                    />
                                </Suspense>
                            )}

                            {activeTab === 'journal' && (
                                <Suspense fallback={<div className="rounded-3xl border border-white/10 bg-white/5 p-8 text-center text-sm text-white/40">Загрузка журнала...</div>}>
                                    <JournalTab
                                        recentActions={recentActions}
                                        filteredRecentActions={filteredRecentActions}
                                        actionSearch={actionSearch}
                                        actionFilter={actionFilter}
                                        onActionSearchChange={setActionSearch}
                                        onActionFilterChange={setActionFilter}
                                        historyActionLabels={historyActionLabels}
                                        formatHistoryDetails={formatHistoryDetails}
                                        contests={contests}
                                        onOpenContest={handleOpenContestById}
                                    />
                                </Suspense>
                            )}



                            {activeTab === 'channels' && (
                                <motion.div key="channels" className="space-y-4">
                                    <GlassCard className="p-4 border-white/5">
                                        <div className="grid grid-cols-3 gap-2">
                                            {[
                                                { label: 'Telegram', value: channels?.length || 0 },
                                                { label: 'YouTube', value: youtubeChannels?.length || 0 },
                                                { label: 'TikTok', value: tiktokChannels?.length || 0 },
                                            ].map((item) => (
                                                <div key={item.label} className="rounded-xl bg-white/5 px-2 py-3 text-center">
                                                    <div className="text-lg font-black text-white">{item.value}</div>
                                                    <div className="mt-1 text-[8px] font-bold uppercase tracking-wider text-white/35">{item.label}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </GlassCard>

                                    {addingChannelType && (
                                        <motion.div
                                            initial={{ opacity: 0, scale: 0.9 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            className="mb-6 bg-white/5 p-4 rounded-2xl border border-white/10 space-y-3"
                                        >
                                            <div className="flex justify-between items-center mb-2">
                                                <h4 className="font-bold text-sm">
                                                    Добавить {addingChannelType === 'telegram' ? 'Telegram' : addingChannelType === 'youtube' ? 'YouTube' : 'TikTok'}
                                                </h4>
                                                <button onClick={() => setAddingChannelType(null)} className="text-white/40">
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                            <input
                                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary/50 transition-colors"
                                                placeholder={
                                                    addingChannelType === 'telegram'
                                                        ? "@username канала"
                                                        : addingChannelType === 'youtube'
                                                            ? "ID канала (UC...)"
                                                            : "@username или ссылка TikTok"
                                                }
                                                value={newChannelInput}
                                                onChange={e => setNewChannelInput(e.target.value)}
                                            />
                                            <div className="flex space-x-3">
                                                <Button
                                                    onClick={handleAddChannel}
                                                    isLoading={isAddingChannel}
                                                    disabled={!newChannelInput}
                                                    className="w-full"
                                                >
                                                    Добавить
                                                </Button>
                                            </div>
                                            {error && (
                                                <div className="mt-2 text-[10px] text-red-400 font-medium flex items-center bg-red-500/10 p-2 rounded-lg border border-red-500/20">
                                                    <AlertCircle size={12} className="mr-2 shrink-0" />
                                                    {error}
                                                </div>
                                            )}
                                            {addingChannelType === 'telegram' && !error && (
                                                <p className="text-[10px] text-white/30 px-2">
                                                    Бот должен быть администратором в канале перед добавлением.
                                                </p>
                                            )}
                                        </motion.div>
                                    )}

                                    <div className="space-y-6">
                                        {/* Telegram Channels */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between px-1">
                                                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Telegram Каналы</h3>
                                                <button
                                                    onClick={() => { setAddingChannelType('telegram'); setNewChannelInput(''); setError(null); }}
                                                    className="text-[10px] font-black uppercase text-white bg-primary px-3 py-1.5 rounded-lg flex items-center space-x-1 active:scale-95 transition-all shadow-lg shadow-primary/20"
                                                >
                                                    <Plus size={14} />
                                                    <span>Добавить</span>
                                                </button>
                                            </div>
                                            {channels?.map((ch, i) => (
                                                <GlassCard 
                                                    key={i} 
                                                    className={cn(
                                                        "relative p-4 flex items-center justify-between border-white/5 group",
                                                        activeChannelId === ch.channel_id ? "z-20" : "z-0"
                                                    )}
                                                >
                                                    <div className="flex items-center space-x-4 min-w-0 flex-1">
                                                        <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center text-primary font-black shrink-0">
                                                            {ch.channel_title.charAt(0)}
                                                        </div>
                                                        <div className="overflow-hidden min-w-0">
                                                            <div className="text-sm font-bold truncate pr-2">{ch.channel_title}</div>
                                                            <div className="text-[10px] text-white/40 truncate">
                                                                @{ch.channel_username?.replace('@', '')}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Gear Icon */}
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); setActiveChannelId(activeChannelId === ch.channel_id ? null : ch.channel_id); }}
                                                        className="p-2 text-white/20 hover:text-white/60 transition-colors rounded-lg hover:bg-white/5 shrink-0 ml-2"
                                                    >
                                                        <Settings size={16} />
                                                    </button>

                                                    {/* Settings Menu */}
                                                    {activeChannelId === ch.channel_id && (
                                                        <motion.div
                                                            initial={{ opacity: 0, scale: 0.9 }}
                                                            animate={{ opacity: 1, scale: 1 }}
                                                            className="absolute right-2 top-12 z-10 w-48 bg-[#1c1c1e] border border-white/10 rounded-xl shadow-2xl overflow-hidden"
                                                        >
                                                            <div className="p-1 space-y-1">
                                                                <button
                                                                    className="w-full flex items-center space-x-2 px-3 py-2 text-xs font-medium text-white/60 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                                                                    onClick={() => handleUpdateChannel(ch.channel_id, ch.channel_username || '')}
                                                                >
                                                                    <RefreshCw size={14} />
                                                                    <span>Обновить данные</span>
                                                                </button>
                                                                <button
                                                                    className="w-full flex items-center space-x-2 px-3 py-2 text-xs font-medium text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                                                    onClick={() => handleDeleteChannel(ch.channel_id)}
                                                                >
                                                                    <Trash2 size={14} />
                                                                    <span>Удалить канал</span>
                                                                </button>
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </GlassCard>
                                            ))}
                                            {(!channels || channels.length === 0) && <p className="text-xs text-white/20 text-center py-4">Нет подключенных каналов</p>}
                                        </div>

                                        {/* YouTube Channels */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between px-1">
                                                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">YouTube Каналы</h3>
                                                <button
                                                    onClick={() => { setAddingChannelType('youtube'); setNewChannelInput(''); }}
                                                    className="text-[10px] font-black uppercase text-red-500 bg-red-500/10 px-3 py-1.5 rounded-lg flex items-center space-x-1 active:scale-95 transition-all"
                                                >
                                                    <Plus size={14} />
                                                    <span>Добавить</span>
                                                </button>
                                            </div>
                                            {youtubeChannels?.map((ch, i) => (
                                                <GlassCard 
                                                    key={i} 
                                                    className={cn(
                                                        "relative p-4 flex items-center justify-between border-white/5 bg-red-500/5 group",
                                                        activeChannelId === ch.channel_id ? "z-20" : "z-0"
                                                    )}
                                                >
                                                    <div className="flex items-center space-x-4 min-w-0 flex-1">
                                                        <div className="w-10 h-10 bg-red-500/20 rounded-xl flex items-center justify-center text-red-500 font-black shrink-0">
                                                            <Youtube size={20} />
                                                        </div>
                                                        <div className="overflow-hidden min-w-0">
                                                            <div className="text-sm font-bold truncate pr-2">{ch.title}</div>
                                                            <div className="text-[10px] text-white/40 truncate">{ch.channel_id}</div>
                                                        </div>
                                                    </div>

                                                    {/* Gear Icon */}
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); setActiveChannelId(activeChannelId === ch.channel_id ? null : ch.channel_id); }}
                                                        className="p-2 text-white/20 hover:text-white/60 transition-colors rounded-lg hover:bg-white/5 shrink-0 ml-2"
                                                    >
                                                        <Settings size={16} />
                                                    </button>

                                                    {/* Settings Menu */}
                                                    {activeChannelId === ch.channel_id && (
                                                        <motion.div
                                                            initial={{ opacity: 0, scale: 0.9 }}
                                                            animate={{ opacity: 1, scale: 1 }}
                                                            className="absolute right-2 top-12 z-10 w-48 bg-[#1c1c1e] border border-white/10 rounded-xl shadow-2xl overflow-hidden"
                                                        >
                                                            <div className="p-1 space-y-1">
                                                                <button
                                                                    className="w-full flex items-center space-x-2 px-3 py-2 text-xs font-medium text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                                                    onClick={() => handleDeleteYoutubeChannel(ch.channel_id)}
                                                                >
                                                                    <Trash2 size={14} />
                                                                    <span>Удалить канал</span>
                                                                </button>
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </GlassCard>
                                            ))}
                                            {(!youtubeChannels || youtubeChannels.length === 0) && <p className="text-xs text-white/20 text-center py-4">Нет YouTube каналов</p>}
                                        </div>

                                        {/* TikTok Channels */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between px-1">
                                                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">TikTok аккаунты</h3>
                                                <button
                                                    onClick={() => { setAddingChannelType('tiktok'); setNewChannelInput(''); setError(null); }}
                                                    className="text-[10px] font-black uppercase text-white/80 bg-white/10 px-3 py-1.5 rounded-lg flex items-center space-x-1 active:scale-95 transition-all"
                                                >
                                                    <Plus size={14} />
                                                    <span>Добавить</span>
                                                </button>
                                            </div>
                                            {tiktokChannels?.map((ch, i) => (
                                                <GlassCard
                                                    key={i}
                                                    className={cn(
                                                        "relative p-4 flex items-center justify-between border-white/5 bg-white/[0.03] group",
                                                        activeChannelId === ch.channel_id ? "z-20" : "z-0"
                                                    )}
                                                >
                                                    <div className="flex items-center space-x-4 min-w-0 flex-1">
                                                        <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center text-white/80 font-black shrink-0">
                                                            <Music2 size={20} />
                                                        </div>
                                                        <div className="overflow-hidden min-w-0">
                                                            <div className="text-sm font-bold truncate pr-2">{ch.title}</div>
                                                            <div className="text-[10px] text-white/40 truncate">@{ch.channel_id.replace(/^@/, '')}</div>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); setActiveChannelId(activeChannelId === ch.channel_id ? null : ch.channel_id); }}
                                                        className="p-2 text-white/20 hover:text-white/60 transition-colors rounded-lg hover:bg-white/5 shrink-0 ml-2"
                                                    >
                                                        <Settings size={16} />
                                                    </button>
                                                    {activeChannelId === ch.channel_id && (
                                                        <motion.div
                                                            initial={{ opacity: 0, scale: 0.9 }}
                                                            animate={{ opacity: 1, scale: 1 }}
                                                            className="absolute right-2 top-12 z-10 w-48 bg-[#1c1c1e] border border-white/10 rounded-xl shadow-2xl overflow-hidden"
                                                        >
                                                            <div className="p-1 space-y-1">
                                                                <button
                                                                    className="w-full flex items-center space-x-2 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                                                    onClick={() => handleDeleteTikTokChannel(ch.channel_id)}
                                                                >
                                                                    <Trash2 size={14} />
                                                                    <span>Удалить аккаунт</span>
                                                                </button>
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </GlassCard>
                                            ))}
                                            {(!tiktokChannels || tiktokChannels.length === 0) && <p className="text-xs text-white/20 text-center py-4">Нет TikTok аккаунтов</p>}
                                        </div>

                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};
