import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import { useTelegram } from '../hooks/useTelegram';
import { GlassCard, ConditionItem } from '../components/ui/Cards';
import { Button } from '../components/ui/Button';
import { Trophy, Users, Clock, CheckCircle } from 'lucide-react';

interface ContestInfo {
    id: number;
    title: string;
    description: string;
    image_url: string | null;
    end_date: string;
    prize_count: number;
    participants_count: number;
}

interface AutoCheckResponse {
    can_register: boolean;
    is_registered: boolean;
    conditions: Array<{
        type: 'telegram' | 'youtube';
        id: string | number;
        title: string;
        met: boolean;
        connected?: boolean;
    }>;
}

export const RegistrationPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const { initData, hapticFeedback, tg, userId } = useTelegram();
    const [isRegistering, setIsRegistering] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);

    const contestId = searchParams.get('contest_id');

    // Fetch Contest Info
    const { data: contest, isLoading: isContestLoading } = useQuery<ContestInfo>({
        queryKey: ['contest', contestId],
        queryFn: async () => {
            const res = await axios.get(`/api/contests/${contestId}`, {
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!contestId,
    });

    // Polling Status
    const { data: status, refetch: refetchStatus } = useQuery<AutoCheckResponse>({
        queryKey: ['status', contestId, initData],
        queryFn: async () => {
            const res = await axios.get(`/api/contests/${contestId}/auto-check`, {
                headers: { 'X-Telegram-Init-Data': initData },
                params: { user_id: userId, _auth: initData }
            });
            return res.data;
        },
        enabled: !!contestId && !!initData && !isSuccess,
        refetchInterval: (query) => (query.state.data?.is_registered || isSuccess) ? false : 3000,
    });

    // Auto-registration logic
    useEffect(() => {
        if (status?.can_register && !status?.is_registered && !isRegistering && !isSuccess) {
            handleRegister();
        }
        if (status?.is_registered && !isSuccess) {
            handleSuccess();
        }
    }, [status, isRegistering, isSuccess]);

    const handleRegister = async () => {
        setIsRegistering(true);
        try {
            await axios.post(`/api/contests/${contestId}/register`, {}, {
                headers: { 'X-Telegram-Init-Data': initData },
                params: { _auth: initData, user_id: userId }
            });
            hapticFeedback('medium');
            refetchStatus();
        } catch (err) {
            console.error('Registration failed', err);
        } finally {
            setIsRegistering(false);
        }
    };

    const handleSuccess = () => {
        setIsSuccess(true);
        hapticFeedback('heavy');
        confetti({
            particleCount: 150,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#8b5cf6', '#d946ef', '#3b82f6']
        });
    };

    const handleConditionAction = (condition: any) => {
        hapticFeedback('light');
        if (condition.type === 'telegram') {
            const url = condition.id.toString().startsWith('-100')
                ? `https://t.me/c/${condition.id.toString().replace('-100', '')}`
                : `https://t.me/${condition.title.replace('@', '')}`;
            tg.openTelegramLink(url);
        } else if (condition.type === 'youtube') {
            if (condition.connected) {
                let url = '';
                const yid = condition.id.toString().trim();
                if (yid.startsWith('http')) url = yid;
                else if (yid.startsWith('@')) url = `https://youtube.com/${yid}`;
                else if (yid.startsWith('UC') || yid.startsWith('HC')) url = `https://youtube.com/channel/${yid}`;
                else if (yid.length === 22) url = `https://youtube.com/channel/UC${yid}`;
                else url = `https://youtube.com/@${yid}`;
                tg.openLink(url);
            } else {
                tg.openLink(`${window.location.origin}/api/youtube/auth?contest_id=${contestId}&user_id=${userId}&_auth=${encodeURIComponent(initData)}`);
            }
        }
    };

    if (isContestLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="spinner" />
                <p className="text-white/40 text-sm animate-pulse">Загружаем информацию о конкурсе...</p>
            </div>
        );
    }

    if (!contest) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 px-6 text-center">
                <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center text-red-500">
                    <Trophy size={40} className="opacity-50" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-xl font-bold">Конкурс недоступен</h2>
                    <p className="text-sm text-white/40 italic">
                        Этот конкурс еще не опубликован, завершен или не существует.
                    </p>
                </div>
                <Button variant="secondary" onClick={() => tg.close()}>Закрыть</Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <AnimatePresence>
                {isSuccess ? (
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="flex flex-col items-center justify-center py-10 space-y-4 text-center"
                    >
                        <div className="w-24 h-24 bg-emerald-500/20 rounded-full flex items-center justify-center text-emerald-400">
                            <CheckCircle size={48} />
                        </div>
                        <div className="space-y-2">
                            <h1 className="text-3xl font-bold">Вы участвуете!</h1>
                            <p className="text-white/60">Все условия выполнены. Ожидайте результатов розыгрыша.</p>
                        </div>
                        <Button variant="secondary" onClick={() => tg.close()}>Закрыть</Button>
                    </motion.div>
                ) : (
                    <>
                        <header className="space-y-4">
                            {contest.image_url ? (
                                <img src={contest.image_url} alt={contest.title} className="w-full aspect-video object-cover rounded-2xl shadow-2xl" />
                            ) : (
                                <div className="w-full aspect-video bg-gradient-to-br from-primary/20 to-secondary/20 rounded-2xl flex items-center justify-center border border-white/10">
                                    <Trophy size={64} className="text-primary/40" />
                                </div>
                            )}
                            <div className="px-1 pt-2">
                                <h1 className="text-2xl font-bold text-white mb-2">{contest.title}</h1>
                                <div className="flex items-center space-x-4 text-white/60 text-xs">
                                    <div className="flex items-center space-x-1.5">
                                        <Users size={14} className="text-primary" />
                                        <span>{contest.participants_count} участников</span>
                                    </div>
                                    <div className="flex items-center space-x-1.5">
                                        <Trophy size={14} className="text-amber-400" />
                                        <span>{contest.prize_count} призов</span>
                                    </div>
                                </div>
                            </div>
                        </header>

                        <section className="space-y-3">
                            <h2 className="text-sm font-bold uppercase tracking-wider text-white/40 px-1">Условия участия</h2>
                            <GlassCard className="p-2 space-y-2">
                                {status?.conditions.map((condition, idx) => (
                                    <ConditionItem
                                        key={idx}
                                        type={condition.type}
                                        label={condition.title}
                                        isMet={condition.met}
                                        isConnected={condition.connected}
                                        onAction={() => handleConditionAction(condition)}
                                    />
                                ))}
                                {(!status || status.conditions.length === 0) && (
                                    <p className="p-4 text-center text-white/40 text-sm">Условий пока нет</p>
                                )}
                            </GlassCard>
                        </section>

                        <footer className="pt-4">
                            <GlassCard className="bg-primary/5 border-primary/20 p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center space-x-2 text-white/80">
                                        <Clock size={16} className="text-primary" />
                                        <span className="text-sm font-medium">Розыгрыш: {new Date(contest.end_date).toLocaleDateString()}</span>
                                    </div>
                                    <div className="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded">АКТИВЕН</div>
                                </div>

                                {status?.is_registered ? (
                                    <div className="w-full bg-emerald-500/10 text-emerald-400 py-3 rounded-xl border border-emerald-500/20 text-center font-bold">
                                        ВЫ УЧАСТВУЕТЕ
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
                                            <motion.div
                                                initial={{ width: 0 }}
                                                animate={{ width: `${(status?.conditions.filter(c => c.met).length || 0) / (status?.conditions.length || 1) * 100}%` }}
                                                className="bg-primary h-full rounded-full shadow-[0_0_10px_rgba(139,92,246,0.5)]"
                                            />
                                        </div>
                                        <p className="text-center text-[10px] text-white/40 uppercase font-bold tracking-widest">
                                            {status?.can_register ? 'Подготовка к регистрации...' : 'Выполните все условия выше'}
                                        </p>
                                    </div>
                                )}
                            </GlassCard>
                        </footer>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
};
