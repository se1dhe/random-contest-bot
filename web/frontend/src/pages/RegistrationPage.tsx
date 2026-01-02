import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import { useTelegram } from '../hooks/useTelegram';
import { GlassCard, ConditionItem } from '../components/ui/Cards';
import { Button } from '../components/ui/Button';
import { Trophy, Users, Clock, CheckCircle, Crown, Gift } from 'lucide-react';
import { CountdownTimer } from '../components/ui/CountdownTimer';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ContestInfo {
    id: number;
    title: string;
    description: string;
    image_url: string | null;
    end_date: string;
    prize_count: number;
    participants_count: number;
    prizes?: Array<{ id: number; place: number; title: string; description?: string | null }>;
}

interface AutoCheckResponse {
    can_register: boolean;
    is_registered: boolean;
    conditions: Array<{
        type: 'telegram' | 'youtube';
        id: string | number;
        title: string;
        username?: string | null;
        invite_link?: string | null;
        met: boolean;
        connected?: boolean;
    }>;
    participants_count?: number;
}

interface Winner {
    place: number;
    title: string;
    user_id: number;
    username: string;
    firstname: string | null;
}

export const RegistrationPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const { initData, hapticFeedback, tg, userId } = useTelegram();
    const [isRegistering, setIsRegistering] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [liveParticipantsCount, setLiveParticipantsCount] = useState<number | null>(null);
    const [contestEnded, setContestEnded] = useState(false);
    const [winners, setWinners] = useState<Winner[]>([]);
    const [revealedWinners, setRevealedWinners] = useState<number>(0);
    const [drawComplete, setDrawComplete] = useState(false);
    const [prizesOpen, setPrizesOpen] = useState(false);

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

    // Synchronize live count with initial data
    useEffect(() => {
        if (contest?.participants_count !== undefined) {
            setLiveParticipantsCount(contest.participants_count);
        }
    }, [contest?.participants_count]);

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
        enabled: !!contestId && !!initData,
        refetchInterval: 3000,
    });

    const handleRegister = React.useCallback(async () => {
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
    }, [contestId, initData, userId, hapticFeedback, refetchStatus]);

    const handleSuccess = React.useCallback(() => {
        setIsSuccess(true);
        hapticFeedback('heavy');
        confetti({
            particleCount: 150,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#8b5cf6', '#d946ef', '#3b82f6']
        });
    }, [hapticFeedback]);

    // Auto-registration logic
    useEffect(() => {
        if (status?.can_register && !status?.is_registered && !isRegistering && !isSuccess) {
            handleRegister();
        }
        if (status?.is_registered && !isSuccess) {
            handleSuccess();
        }
        if (status?.participants_count !== undefined) {
            setLiveParticipantsCount(status.participants_count);
        }
    }, [status, isRegistering, isSuccess, handleRegister, handleSuccess]);

    // WebSocket for live updates
    useEffect(() => {
        if (!contestId) return;

        let socket: WebSocket | null = null;
        let reconnectTimer: number | null = null;

        const connect = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/ws/${contestId}`;
            socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                if (reconnectTimer) {
                    window.clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'new_registration') {
                        setLiveParticipantsCount(data.participants_count);
                    }
                } catch (err) {
                    console.error('WS Message Error:', err);
                }
            };

            socket.onerror = (err) => console.error('WebSocket Error:', err);

            socket.onclose = () => {
                // Автоматический реконнект через 2 секунды
                reconnectTimer = window.setTimeout(() => connect(), 2000);
            };
        };

        connect();

        return () => {
            if (reconnectTimer) {
                window.clearTimeout(reconnectTimer);
            }
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.close();
            }
        };
    }, [contestId]);

    // Handle countdown end - fetch winners and start animation
    const handleCountdownEnd = async () => {
        setContestEnded(true);
        hapticFeedback('heavy');

        // Wait a moment for dramatic effect
        await new Promise(resolve => setTimeout(resolve, 1000));

        try {
            const res = await axios.get(`/api/contests/${contestId}/results-info`, {
                params: { user_id: userId, _auth: initData }
            });

            if (res.data.winners && res.data.winners.length > 0) {
                setWinners(res.data.winners);
                startWinnerReveal(res.data.winners);
            } else {
                setDrawComplete(true);
            }
        } catch (error) {
            console.error('Failed to fetch winners:', error);
            setDrawComplete(true);
        }
    };

    // Animate winner reveals
    const startWinnerReveal = (winnersList: Winner[]) => {
        const revealNextWinner = (index: number) => {
            if (index >= winnersList.length) {
                setDrawComplete(true);
                return;
            }

            setTimeout(() => {
                setRevealedWinners(index + 1);

                // Confetti for first place
                if (index === 0) {
                    confetti({
                        particleCount: 200,
                        spread: 100,
                        origin: { y: 0.4 },
                        colors: ['#fbbf24', '#f59e0b', '#d97706']
                    });
                } else {
                    confetti({
                        particleCount: 50,
                        spread: 60,
                        origin: { y: 0.6 },
                        colors: ['#8b5cf6', '#d946ef', '#3b82f6']
                    });
                }

                hapticFeedback('light');
                revealNextWinner(index + 1);
            }, index === 0 ? 1200 : 800);
        };

        revealNextWinner(0);
    };

    const handleConditionAction = (condition: AutoCheckResponse['conditions'][number]) => {
        hapticFeedback('light');
        if (condition.type === 'telegram') {
            let url = '';
            if (condition.username && condition.username.trim().length > 0) {
                const uname = condition.username.replace('@', '').trim();
                url = `https://t.me/${uname}`;
            } else if (condition.invite_link && condition.invite_link.trim().length > 0) {
                url = condition.invite_link.trim();
            } else {
                const idStr = condition.id.toString();
                if (idStr.startsWith('-100')) {
                    url = `https://t.me/c/${idStr.replace('-100', '')}`;
                } else {
                    url = `https://t.me/${idStr}`;
                }
            }
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

    // Show winner reveal animation
    if (contestEnded && winners.length > 0) {
        return (
            <div className="space-y-6 pb-10">
                <header className="space-y-4">
                    {contest.image_url ? (
                        <motion.img
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            src={contest.image_url}
                            alt={contest.title}
                            className="w-full aspect-video object-cover rounded-2xl shadow-2xl"
                        />
                    ) : (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="w-full aspect-video bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-2xl flex items-center justify-center border border-amber-500/20"
                        >
                            <Trophy size={80} className="text-amber-500/40" />
                        </motion.div>
                    )}

                    <div className="text-center space-y-3">
                        <motion.div
                            initial={{ scale: 0.5, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            className="inline-flex p-3 bg-amber-500/10 rounded-full text-amber-500"
                        >
                            <Trophy size={32} />
                        </motion.div>
                        <h1 className="text-2xl font-bold tracking-tight">{contest.title}</h1>
                        <p className="text-sm text-white/60">🎉 Розыгрыш завершён!</p>
                    </div>
                </header>

                <section className="space-y-4">
                    <div className="flex items-center justify-between px-1">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-white/40">
                            Победители
                        </h2>
                        {!drawComplete && (
                            <motion.div
                                animate={{ opacity: [0.4, 1, 0.4] }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                                className="text-xs text-primary font-medium"
                            >
                                Объявление результатов...
                            </motion.div>
                        )}
                    </div>

                    <div className="space-y-3">
                        <AnimatePresence mode="popLayout">
                            {winners.slice(0, revealedWinners).map((winner, idx) => (
                                <motion.div
                                    key={idx}
                                    initial={{ scale: 0.8, opacity: 0, y: 20 }}
                                    animate={{ scale: 1, opacity: 1, y: 0 }}
                                    transition={{
                                        type: "spring",
                                        stiffness: 200,
                                        damping: 20
                                    }}
                                >
                                    <GlassCard className={cn(
                                        'p-4 flex items-center justify-between transition-all',
                                        winner.place === 1 && 'bg-amber-500/10 border-amber-500/30 shadow-lg shadow-amber-500/10'
                                    )}>
                                        <div className="flex items-center space-x-4">
                                            <motion.div
                                                initial={{ rotate: -180, scale: 0 }}
                                                animate={{ rotate: 0, scale: 1 }}
                                                transition={{ delay: 0.2, type: "spring" }}
                                                className={cn(
                                                    'w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg',
                                                    winner.place === 1
                                                        ? 'bg-gradient-to-br from-amber-400 to-amber-600 text-white shadow-lg shadow-amber-500/30'
                                                        : 'bg-white/10 text-white/80'
                                                )}
                                            >
                                                {winner.place === 1 ? <Crown size={24} /> : winner.place}
                                            </motion.div>
                                            <div className="flex flex-col cursor-pointer" onClick={() => {
                                                const url = winner.username
                                                    ? `https://t.me/${winner.username}`
                                                    : `tg://user?id=${winner.user_id}`;
                                                tg.openTelegramLink(url);
                                            }}>
                                                <motion.div
                                                    initial={{ x: -10, opacity: 0 }}
                                                    animate={{ x: 0, opacity: 1 }}
                                                    transition={{ delay: 0.3 }}
                                                    className="font-bold text-white leading-tight hover:text-primary transition-colors"
                                                >
                                                    {winner.username ? `@${winner.username}` : (winner.firstname || 'Участник')}
                                                </motion.div>
                                                <motion.span
                                                    initial={{ x: -10, opacity: 0 }}
                                                    animate={{ x: 0, opacity: 1 }}
                                                    transition={{ delay: 0.4 }}
                                                    className="text-xs text-white/50 truncate max-w-[180px]"
                                                >
                                                    {winner.title}
                                                </motion.span>
                                            </div>
                                        </div>
                                        <motion.div
                                            initial={{ scale: 0 }}
                                            animate={{ scale: 1 }}
                                            transition={{ delay: 0.5, type: "spring" }}
                                            className="text-amber-500/60"
                                        >
                                            <Gift size={20} />
                                        </motion.div>
                                    </GlassCard>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </section>

                {drawComplete && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center pt-4"
                    >
                        <p className="text-xs text-white/30 mb-4">🎉 Поздравляем всех победителей!</p>
                        <Button variant="secondary" onClick={() => tg.close()}>Закрыть</Button>
                    </motion.div>
                )}
            </div>
        );
    }

    return (
        <div className="space-y-6">
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
                            <span>{liveParticipantsCount ?? contest.participants_count} участников</span>
                        </div>
                        <button
                            type="button"
                            className="flex items-center space-x-1.5 hover:text-white transition-colors"
                            onClick={() => setPrizesOpen(true)}
                        >
                            <Trophy size={14} className="text-amber-400" />
                            <span>{contest.prize_count} призов</span>
                        </button>
                    </div>
                </div>
            </header>

            {contest.end_date && (
                <CountdownTimer endDate={contest.end_date} onEnd={handleCountdownEnd} />
            )}

            <AnimatePresence mode="wait">
                {isSuccess ? (
                    <motion.div
                        key="success-banner"
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="glass-card p-6 flex flex-col items-center justify-center space-y-4 text-center border-emerald-500/20 bg-emerald-500/5"
                    >
                        <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center text-emerald-400">
                            <CheckCircle size={32} />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-xl font-bold text-emerald-400">Вы участвуете!</h3>
                            <p className="text-xs text-white/60">Все условия выполнены. Ожидайте результатов розыгрыша.</p>
                        </div>
                        <Button variant="secondary" onClick={() => tg.close()}>Закрыть</Button>
                    </motion.div>
                ) : (
                    <motion.div
                        key="conditions-form"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="space-y-6"
                    >
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

                        <footer className="pt-2">
                            <GlassCard className="bg-primary/5 border-primary/20 p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center space-x-2 text-white/80">
                                        <Clock size={16} className="text-primary" />
                                        <span className="text-sm font-medium">Розыгрыш: {new Date(contest.end_date).toLocaleDateString()}</span>
                                    </div>
                                    <div className="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded">АКТИВЕН</div>
                                </div>

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
                            </GlassCard>
                        </footer>
                    </motion.div>
                )}
            </AnimatePresence>
            {prizesOpen && (
                <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50">
                    <div className="w-full sm:max-w-md bg-[#1c1c1e] border border-white/10 rounded-t-2xl sm:rounded-2xl shadow-2xl">
                        <div className="p-4 border-b border-white/10 flex items-center justify-between">
                            <div className="flex items-center space-x-2 text-white">
                                <Trophy size={18} className="text-amber-400" />
                                <span className="text-sm font-bold">Призы конкурса</span>
                            </div>
                            <button
                                className="text-white/50 hover:text-white transition-colors"
                                onClick={() => setPrizesOpen(false)}
                            >
                                ✕
                            </button>
                        </div>
                        <div className="p-4 space-y-3 max-h-[60vh] overflow-auto">
                            {contest.prizes && contest.prizes.length > 0 ? (
                                contest.prizes.map((p) => (
                                    <GlassCard key={p.id ?? `${p.place}-${p.title}`} className="p-3">
                                        <div className="flex items-center space-x-3">
                                            <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center text-amber-400 font-bold">
                                                {p.place}
                                            </div>
                                            <div className="flex-1">
                                                <div className="text-sm font-bold">{p.title}</div>
                                                {p.description && (
                                                    <div className="text-xs text-white/60 mt-1">{p.description}</div>
                                                )}
                                            </div>
                                        </div>
                                    </GlassCard>
                                ))
                            ) : (
                                <p className="text-white/40 text-sm">Призы не настроены</p>
                            )}
                        </div>
                        <div className="p-4 border-t border-white/10">
                            <Button variant="secondary" className="w-full" onClick={() => setPrizesOpen(false)}>Закрыть</Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
