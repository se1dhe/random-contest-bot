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
    Trash2
} from 'lucide-react';
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

    const { data: contests, refetch: refetchContests } = useQuery<any[]>({
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

    const { data: channels } = useQuery<any[]>({
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
                                    <Button variant="secondary" className="w-full text-red-500/60 border-red-500/10">
                                        <Trash2 size={18} className="mr-2" /> ОСТАНОВИТЬ КОНКУРС
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
                        <header className="flex items-center justify-between px-1">
                            <h1 className="text-2xl font-black italic tracking-tighter">ADMIN <span className="text-primary">PANEL</span></h1>
                            <Button variant="secondary" className="p-2 w-10 h-10 rounded-full">
                                <Settings size={18} />
                            </Button>
                        </header>

                        {/* Stats Quick Grid */}
                        <div className="grid grid-cols-2 gap-3">
                            <GlassCard className="p-3 bg-primary/5 hover:bg-primary/10 transition-colors">
                                <div className="flex items-center space-x-2 text-white/40 mb-1">
                                    <Trophy size={14} />
                                    <span className="text-[10px] font-bold uppercase tracking-wider">Всего конкурсов</span>
                                </div>
                                <div className="text-2xl font-bold">{contests?.length || 0}</div>
                            </GlassCard>
                            <GlassCard className="p-3 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors">
                                <div className="flex items-center space-x-2 text-emerald-400/40 mb-1">
                                    <TrendingUp size={14} />
                                    <span className="text-[10px] font-bold uppercase tracking-wider">Активные</span>
                                </div>
                                <div className="text-2xl font-bold flex items-baseline">
                                    {contests?.filter(c => c.status === 'active').length || 0}
                                    <span className="text-[10px] ml-1 text-emerald-400">/ {channels?.length || 0}</span>
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
                                        {contests?.map((c, i) => (
                                            <GlassCard
                                                key={i}
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
                                    </div>
                                </motion.div>
                            )}

                            {activeTab === 'dash' && (
                                <motion.div key="dash" className="py-20 text-center">
                                    <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto text-primary mb-6 animate-pulse">
                                        <TrendingUp size={40} />
                                    </div>
                                    <h3 className="text-xl font-bold mb-2">Аналитика</h3>
                                    <p className="text-sm text-white/40 max-w-[200px] mx-auto italic">Общая статистика по всем вашим конкурсам будет здесь</p>
                                </motion.div>
                            )}

                            {activeTab === 'channels' && (
                                <motion.div key="channels" className="space-y-4">
                                    <div className="flex items-center justify-between px-1">
                                        <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Подключенные каналы</h3>
                                        <button className="text-[10px] font-black uppercase text-secondary bg-white/5 px-3 py-1.5 rounded-lg flex items-center space-x-1">
                                            <Plus size={14} />
                                            <span>Добавить</span>
                                        </button>
                                    </div>
                                    <div className="space-y-3">
                                        {channels?.map((ch, i) => (
                                            <GlassCard key={i} className="p-4 flex items-center justify-between border-white/5">
                                                <div className="flex items-center space-x-4">
                                                    <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center text-primary font-black">
                                                        {ch.channel_title.charAt(0)}
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-bold">{ch.channel_title}</div>
                                                        <div className="text-[10px] text-white/40">@{ch.channel_username}</div>
                                                    </div>
                                                </div>
                                                <div className="text-white/20">
                                                    <Settings size={16} />
                                                </div>
                                            </GlassCard>
                                        ))}
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
