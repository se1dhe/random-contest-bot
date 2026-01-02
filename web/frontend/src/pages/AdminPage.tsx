import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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
    TrendingUp,
    ArrowLeft,
    Send,
    CheckCircle2,
    Clock,
    Youtube,
    Trash2,
    RefreshCw,
    AlertCircle
} from 'lucide-react';
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { ContestForm } from '../components/ContestForm';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export const AdminPage: React.FC = () => {
    const { initData, hapticFeedback } = useTelegram();
    const [activeTab, setActiveTab] = useState<'dash' | 'contests' | 'channels'>('dash');
    const [isCreating, setIsCreating] = useState(false);
    const [selectedContest, setSelectedContest] = useState<any>(null);
    const [isPublishing, setIsPublishing] = useState(false);

    // Channel adding state
    const [addingChannelType, setAddingChannelType] = useState<'telegram' | 'youtube' | null>(null);
    const [newChannelInput, setNewChannelInput] = useState('');
    const [isAddingChannel, setIsAddingChannel] = useState(false);
    const [activeChannelId, setActiveChannelId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    const { data: contests, isLoading: isContestsLoading, refetch: refetchContests } = useQuery<any[]>({
        queryKey: ['admin_contests', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/contests', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData,
    });

    const { data: channels, refetch: refetchChannels } = useQuery<any[]>({
        queryKey: ['admin_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData,
    });

    const { data: youtubeChannels, refetch: refetchYoutubeChannels } = useQuery<any[]>({
        queryKey: ['admin_youtube_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/youtube-channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData,
    });

    const { data: analytics, refetch: refetchAnalytics } = useQuery<any>({
        queryKey: ['admin_analytics', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/analytics/overview', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData
    });

    const { data: analyticsGrowth, refetch: refetchGrowth } = useQuery<any[]>({
        queryKey: ['admin_analytics_growth', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/analytics/growth', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData
    });

    const handleTabChange = (tab: any) => {
        hapticFeedback('light');
        setActiveTab(tab);
        setIsCreating(false);
        setSelectedContest(null);
    };

    const handleCreateSuccess = () => {
        setIsCreating(false);
        refetchContests();
    };

    const handleRefreshAll = () => {
        hapticFeedback('medium');
        refetchContests();
        refetchChannels();
        refetchYoutubeChannels();
        refetchAnalytics();
        refetchGrowth();
        setIsSettingsOpen(false);
        hapticFeedback('heavy');
    };

    const handlePublish = async (contestId: number) => {
        setIsPublishing(true);
        hapticFeedback('medium');
        try {
            await axios.post(`/api/publish/contest/${contestId}`, {}, {
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSelectedContest(null);
            refetchContests();
        } catch (err) {
            console.error('Failed to publish', err);
            hapticFeedback('rigid');
        } finally {
            setIsPublishing(false);
        }
    };

    const handleRunContest = async (contestId: number) => {
        if (!confirm('Вы уверены, что хотите завершить конкурс и провести розыгрыш сейчас?')) return;
        setIsPublishing(true);
        hapticFeedback('medium');
        try {
            await axios.post(`/api/admin/contests/${contestId}/draw`, {}, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSelectedContest(null);
            refetchContests();
        } catch (err: any) {
            console.error('Failed to run contest', err);
            hapticFeedback('rigid');
            setError(err.response?.data?.detail || 'Ошибка при проведении розыгрыша');
        } finally {
            setIsPublishing(false);
        }
    };

    const handleDeleteContest = async (contestId: number) => {
        if (!confirm('Вы уверены, что хотите удалить этот конкурс? Это действие необратимо.')) return;
        setIsPublishing(true);
        hapticFeedback('medium');
        try {
            await axios.delete(`/api/admin/contests/${contestId}`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            hapticFeedback('heavy');
            setSelectedContest(null);
            refetchContests();
        } catch (err: any) {
            console.error('Failed to delete contest', err);
            hapticFeedback('rigid');
            setError(err.response?.data?.detail || 'Ошибка при удалении конкурса');
        } finally {
            setIsPublishing(false);
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
                refetchChannels();
            } else {
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
                refetchYoutubeChannels();
            }
            hapticFeedback('heavy');
            setAddingChannelType(null);
            setNewChannelInput('');
        } catch (err: any) {
            console.error('Failed to add channel', err);
            hapticFeedback('rigid');
            setError(err.response?.data?.detail || 'Ошибка при добавлении канала');
        } finally {
            setIsAddingChannel(false);
        }
    };

    const handleDeleteChannel = async (id: number) => {
        if (!confirm('Вы уверены, что хотите удалить этот канал?')) return;
        try {
            await axios.delete(`/api/admin/channels/${id}`, {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            refetchChannels();
            hapticFeedback('heavy');
        } catch (err) {
            console.error('Failed to delete channel', err);
            hapticFeedback('rigid');
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
            refetchChannels();
            hapticFeedback('heavy');
        } catch (err: any) {
            console.error('Failed to update channel', err);
            hapticFeedback('rigid');
            setError('Не удалось обновить данные канала');
        } finally {
            setActiveChannelId(null);
        }
    };

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
                        <ContestForm
                            onSuccess={handleCreateSuccess}
                            onCancel={() => setIsCreating(false)}
                        />
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
                            <GlassCard className="p-5 space-y-4">
                                <div className="flex justify-between items-start">
                                    <div className={cn(
                                        'text-[8px] font-black tracking-widest px-2 py-1 rounded-md uppercase',
                                        selectedContest.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                            selectedContest.status === 'draft' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
                                                'bg-white/5 text-white/20 border border-white/10'
                                    )}>
                                        {selectedContest.status}
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
                                </div>

                                {selectedContest.require_youtube_subscription && (
                                    <div className="pt-4 border-t border-white/5">
                                        <div className="flex items-center space-x-2 text-red-400">
                                            <Youtube size={14} />
                                            <span className="text-[10px] font-bold uppercase tracking-wider">Требуется YouTube ({selectedContest.youtube_subscription_days_required} дн.)</span>
                                        </div>
                                    </div>
                                )}
                            </GlassCard>

                            {selectedContest.status === 'draft' && (
                                <div className="space-y-3">
                                    <Button
                                        onClick={() => handlePublish(selectedContest.id)}
                                        isLoading={isPublishing}
                                        className="w-full bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20"
                                    >
                                        <Send size={18} className="mr-2" /> ОПУБЛИКОВАТЬ В КАНАЛИ
                                    </Button>
                                    <p className="text-[10px] text-center text-white/40 italic px-4">
                                        Конкурс будет немедленно опубликован в выбранном Telegram канале и станет доступен для регистрации.
                                    </p>
                                </div>
                            )}

                                    {selectedContest.status === 'active' && (
                                        <div className="space-y-3">
                                            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center space-x-3 text-emerald-400">
                                                <CheckCircle2 size={24} />
                                                <div className="text-sm font-bold">Конкурс запущен и активен</div>
                                            </div>
                                            <Button
                                                onClick={() => handleRunContest(selectedContest.id)}
                                                isLoading={isPublishing}
                                                className="w-full bg-amber-500 hover:bg-amber-600 text-white shadow-lg shadow-amber-500/20"
                                            >
                                                <Trophy size={18} className="mr-2" /> РАЗЫГРАТЬ СЕЙЧАС
                                            </Button>
                                            <Button
                                                variant="secondary"
                                                onClick={() => handleDeleteContest(selectedContest.id)}
                                                isLoading={isPublishing}
                                                className="w-full text-red-500/60 border-red-500/10 hover:bg-red-500/10"
                                            >
                                                <Trash2 size={18} className="mr-2" /> УДАЛИТЬ КОНКУРС
                                            </Button>
                                        </div>
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
                        <div className="grid grid-cols-2 gap-3">
                            <GlassCard className="p-3 bg-primary/5 hover:bg-primary/10 transition-colors">
                                <div className="flex items-center space-x-2 text-white/40 mb-1">
                                    <Trophy size={14} />
                                    <span className="text-[10px] font-bold uppercase tracking-wider">Всего конкурсов</span>
                                </div>
                                <div className="text-2xl font-bold">{analytics?.total_contests || 0}</div>
                            </GlassCard>
                            <GlassCard className="p-3 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors">
                                <div className="flex items-center space-x-2 text-emerald-400/40 mb-1">
                                    <TrendingUp size={14} />
                                    <span className="text-[10px] font-bold uppercase tracking-wider">Активные</span>
                                </div>
                                <div className="text-2xl font-bold flex items-baseline">
                                    {analytics?.active_contests || 0}
                                    <span className="text-[10px] ml-1 text-emerald-400">/ {analytics?.completed_contests || 0}</span>
                                </div>
                            </GlassCard>
                        </div>

                        {/* Tabs */}
                        <div className="flex bg-white/5 p-1 rounded-xl border border-white/5">
                            {[
                                { id: 'dash', label: 'Обзор' },
                                { id: 'contests', label: 'Конкурсы' },
                                { id: 'channels', label: 'Каналы' }
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => handleTabChange(tab.id as any)}
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
                                    <GlassCard className="p-4 border-white/5 space-y-4">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Рост аудитории</h3>
                                            <div className="text-xs font-bold text-primary flex items-center bg-primary/10 px-2 py-1 rounded-md">
                                                <Users size={12} className="mr-1" />
                                                {analytics?.total_participants || 0}
                                            </div>
                                        </div>
                                        <div className="h-48 w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <AreaChart data={analyticsGrowth}>
                                                    <defs>
                                                        <linearGradient id="colorPart" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                                    <XAxis
                                                        dataKey="date"
                                                        stroke="#ffffff40"
                                                        fontSize={10}
                                                        tickLine={false}
                                                        axisLine={false}
                                                    />
                                                    <Tooltip
                                                        contentStyle={{ backgroundColor: '#1c1c1e', border: '1px solid #ffffff10', borderRadius: '8px' }}
                                                        itemStyle={{ color: '#fff' }}
                                                    />
                                                    <Area
                                                        type="monotone"
                                                        dataKey="participants"
                                                        stroke="#8b5cf6"
                                                        strokeWidth={2}
                                                        fillOpacity={1}
                                                        fill="url(#colorPart)"
                                                        strokeDasharray="5 5"
                                                    />
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </GlassCard>

                                    <div className="grid grid-cols-2 gap-3">
                                        {/* More stats could go here */}
                                    </div>
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

                                    <div className="space-y-3">
                                        {isContestsLoading ? (
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
                                                {contests?.map((c) => (
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
                                                                c.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                                    c.status === 'draft' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
                                                                        'bg-white/5 text-white/20 border border-white/10'
                                                            )}>
                                                                {c.status}
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
                                                {contests?.length === 0 && (
                                                    <div className="py-20 text-center space-y-4">
                                                        <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto text-white/10">
                                                            <Trophy size={32} />
                                                        </div>
                                                        <p className="text-sm text-white/20 italic">Конкурсов пока нет</p>
                                                        <Button variant="secondary" onClick={() => setIsCreating(true)}>Создать первый</Button>
                                                    </div>
                                                )}
                                            </motion.div>
                                        )}
                                    </div>
                                </motion.div>
                            )}



                            {activeTab === 'channels' && (
                                <motion.div key="channels" className="space-y-4">
                                    {addingChannelType && (
                                        <motion.div
                                            initial={{ opacity: 0, scale: 0.9 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            className="mb-6 bg-white/5 p-4 rounded-2xl border border-white/10 space-y-3"
                                        >
                                            <div className="flex justify-between items-center mb-2">
                                                <h4 className="font-bold text-sm">
                                                    Добавить {addingChannelType === 'telegram' ? 'Telegram' : 'YouTube'} канал
                                                </h4>
                                                <button onClick={() => setAddingChannelType(null)} className="text-white/40">
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                            <input
                                                className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary/50 transition-colors"
                                                placeholder={addingChannelType === 'telegram' ? "@username канала" : "ID канала (UC...)"}
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
                                                                    onClick={() => handleUpdateChannel(ch.channel_id, ch.channel_username)}
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
                                                <GlassCard key={i} className="p-4 flex items-center justify-between border-white/5 bg-red-500/5">
                                                    <div className="flex items-center space-x-4">
                                                        <div className="w-10 h-10 bg-red-500/20 rounded-xl flex items-center justify-center text-red-500 font-black shrink-0">
                                                            <Youtube size={20} />
                                                        </div>
                                                        <div className="overflow-hidden">
                                                            <div className="text-sm font-bold truncate">{ch.title}</div>
                                                            <div className="text-[10px] text-white/40">{ch.channel_id}</div>
                                                        </div>
                                                    </div>
                                                </GlassCard>
                                            ))}
                                            {(!youtubeChannels || youtubeChannels.length === 0) && <p className="text-xs text-white/20 text-center py-4">Нет YouTube каналов</p>}
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
