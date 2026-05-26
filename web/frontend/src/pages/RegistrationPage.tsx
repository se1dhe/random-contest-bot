import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import { useTelegram } from '../hooks/useTelegram';
import { GlassCard, ConditionItem } from '../components/ui/Cards';
import { Button } from '../components/ui/Button';
import { Trophy, Users, Clock, CheckCircle, Crown, Gift, Calendar, RefreshCw, ExternalLink, ShieldCheck } from 'lucide-react';
import { CountdownTimer } from '../components/ui/CountdownTimer';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { normalizeLanguage, t, type ContestLanguage } from '../i18n';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ContestInfo {
    id: number;
    title: string;
    description: string;
    language: ContestLanguage;
    image_url: string | null;
    end_date: string;
    prize_count: number;
    participants_count: number;
    require_captcha?: boolean;
    prizes?: Array<{ id: number; place: number; title: string; description?: string | null }>;
}

interface AutoCheckResponse {
    can_register: boolean;
    is_registered: boolean;
    captcha_required?: boolean;
    external_conditions_met?: boolean;
    conditions: Array<{
        type: 'telegram' | 'youtube' | 'tiktok' | 'instagram';
        id: string | number;
        title: string;
        username?: string | null;
        invite_link?: string | null;
        met: boolean;
        connected?: boolean;
        verification_status?: string;
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

interface ResultInfo {
    contest_title: string;
    contest_description?: string | null;
    language?: ContestLanguage;
    image_url?: string | null;
    end_date: string;
    participants_count: number;
    winners: Array<{
        place: number;
        title: string;
        user_id: number;
        username: string | null;
        firstname: string | null;
    }>;
}

export const RegistrationPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const { initData, hapticFeedback, tg, userId, openLink } = useTelegram();
    const [isRegistering, setIsRegistering] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [registerError, setRegisterError] = useState<string | null>(null);
    const [liveParticipantsCount, setLiveParticipantsCount] = useState<number | null>(null);
    const [contestEnded, setContestEnded] = useState(false);
    const [winners, setWinners] = useState<Winner[]>([]);
    const [revealedWinners, setRevealedWinners] = useState<number>(0);
    const [drawComplete, setDrawComplete] = useState(false);
    const [prizesOpen, setPrizesOpen] = useState(false);
    const [pendingExternalAuth, setPendingExternalAuth] = useState<'youtube' | 'tiktok' | 'instagram' | null>(null);
    const [captchaAnswer, setCaptchaAnswer] = useState('');

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

    // Always fetch results info as fallback when конкурс завершен
    const { data: resultsInfo } = useQuery<ResultInfo>({
        queryKey: ['results-info', contestId, initData, userId],
        queryFn: async () => {
            const res = await axios.get(`/api/contests/${contestId}/results-info`, {
                params: { user_id: userId, _auth: initData }
            });
            return res.data;
        },
        enabled: !!contestId && !!initData && !!userId,
    });
    const language = normalizeLanguage(contest?.language || resultsInfo?.language);

    const getConditionStatusText = (condition: AutoCheckResponse['conditions'][number]) => {
        if (pendingExternalAuth === condition.type && !condition.met) {
            return condition.connected ? t(language, 'checkingConnection') : t(language, 'waitingAuth');
        }
        if ((condition.type === 'instagram' || condition.type === 'tiktok') && !condition.met) {
            if (condition.verification_status === 'unverified') {
                return t(language, 'conditionUnverified')
            }
            if (condition.verification_status === 'not_following') {
                return t(language, 'followRequired')
            }
        }
        return undefined;
    };

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

    const { data: captchaChallenge, refetch: refetchCaptcha } = useQuery<{ question: string; token: string; expires_in: number }>({
        queryKey: ['captcha', contestId, initData, userId],
        queryFn: async () => {
            const res = await axios.get(`/api/contests/${contestId}/captcha`, {
                headers: { 'X-Telegram-Init-Data': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!contestId && !!initData && !!userId && !!contest?.require_captcha && !!status?.external_conditions_met && !status?.is_registered,
        staleTime: 0,
    });

    const pendingExternalCondition = useMemo(() => {
        if (!pendingExternalAuth || !status?.conditions) {
            return null;
        }
        return status.conditions.find((condition) => condition.type === pendingExternalAuth) || null;
    }, [pendingExternalAuth, status?.conditions]);

    useEffect(() => {
        if (!pendingExternalAuth || !pendingExternalCondition) {
            return;
        }
        if (pendingExternalCondition.connected || pendingExternalCondition.met) {
            setPendingExternalAuth(null);
        }
    }, [pendingExternalAuth, pendingExternalCondition]);

    const handleRegister = React.useCallback(async () => {
        setIsRegistering(true);
        setRegisterError(null);
        try {
            await axios.post(`/api/contests/${contestId}/register`, {}, {
                headers: { 'X-Telegram-Init-Data': initData },
                params: { _auth: initData, user_id: userId }
            });
            hapticFeedback('medium');
            refetchStatus();
        } catch (err) {
            console.error('Registration failed', err);
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setRegisterError(detail || t(language, 'registrationError'));
            hapticFeedback('rigid');
        } finally {
            setIsRegistering(false);
        }
    }, [contestId, initData, userId, hapticFeedback, refetchStatus, language]);

    const handleCaptchaRegister = React.useCallback(async () => {
        if (!captchaChallenge) {
            await refetchCaptcha();
            return;
        }
        setIsRegistering(true);
        setRegisterError(null);
        try {
            await axios.post(`/api/contests/${contestId}/register`, {
                captcha_token: captchaChallenge.token,
                captcha_answer: captchaAnswer,
            }, {
                headers: { 'X-Telegram-Init-Data': initData },
                params: { _auth: initData, user_id: userId }
            });
            hapticFeedback('medium');
            setCaptchaAnswer('');
            refetchStatus();
        } catch (err) {
            const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setRegisterError(detail || t(language, 'captchaInvalid'));
            hapticFeedback('rigid');
            setCaptchaAnswer('');
            refetchCaptcha();
        } finally {
            setIsRegistering(false);
        }
    }, [captchaAnswer, captchaChallenge, contestId, hapticFeedback, initData, language, refetchCaptcha, refetchStatus, userId]);

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
        if (status?.can_register && !status?.captcha_required && !status?.is_registered && !isRegistering && !isSuccess) {
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
                setPendingExternalAuth('youtube');
                tg.openLink(`${window.location.origin}/api/youtube/auth?contest_id=${contestId}&user_id=${userId}&_auth=${encodeURIComponent(initData)}`);
            }
        } else if (condition.type === 'tiktok') {
            const target = condition.id.toString().trim();
            if (condition.connected) {
                const url = target.startsWith('http') ? target : `https://www.tiktok.com/@${target.replace(/^@/, '')}`;
                tg.openLink(url);
            } else {
                setPendingExternalAuth('tiktok');
                tg.openLink(`${window.location.origin}/api/tiktok/auth?contest_id=${contestId}&user_id=${userId}&_auth=${encodeURIComponent(initData)}`);
            }
        } else if (condition.type === 'instagram') {
            const target = condition.id.toString().trim();
            if (condition.connected) {
                const url = target.startsWith('http') ? target : `https://instagram.com/${target}`;
                tg.openLink(url);
            } else {
                setPendingExternalAuth('instagram');
                openLink(
                    `${window.location.origin}/api/instagram/auth?contest_id=${contestId}&user_id=${userId}&_auth=${encodeURIComponent(initData)}`,
                    { try_browser: 'chrome' }
                );
            }
        }
        setRegisterError(null);
    };

    if (isContestLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="spinner" />
                <p className="text-white/40 text-sm animate-pulse">{t(language, 'loadingContest')}</p>
            </div>
        );
    }

    if (!contest) {
        if (resultsInfo && resultsInfo.winners && resultsInfo.winners.length > 0) {
            return (
                <div className="space-y-6 pb-10">
                    <header className="space-y-4">
                        {resultsInfo.image_url ? (
                            <motion.img
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                src={resultsInfo.image_url}
                                alt={resultsInfo.contest_title}
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
                            <h1 className="text-2xl font-bold tracking-tight">{resultsInfo.contest_title}</h1>
                            <div className="flex items-center justify-center gap-4 text-sm text-white/60">
                                <div className="flex items-center gap-1.5">
                                    <Calendar size={14} />
                                    <span>{new Date(resultsInfo.end_date).toLocaleDateString()}</span>
                                </div>
                                <div className="w-1 h-1 rounded-full bg-white/20" />
                                <div className="flex items-center gap-1.5">
                                    <Users size={14} />
                                    <span>{resultsInfo.participants_count} {t(language, 'participants')}</span>
                                </div>
                            </div>
                        </div>
                    </header>
                    <section className="space-y-4">
                        <div className="flex items-center justify-between px-1">
                            <h2 className="text-sm font-bold uppercase tracking-wider text-white/40">
                                {t(language, 'winners')}
                            </h2>
                        </div>
                        <div className="space-y-3">
                            <AnimatePresence mode="popLayout">
                                {resultsInfo.winners.map((winner, idx) => (
                                    <motion.div
                                        key={idx}
                                        initial={{ scale: 0.8, opacity: 0, y: 20 }}
                                        animate={{ scale: 1, opacity: 1, y: 0 }}
                                        transition={{ type: "spring", stiffness: 200, damping: 20 }}
                                        className="relative overflow-hidden"
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
                                                <div className="flex flex-col">
                                                    <motion.div
                                                        initial={{ x: -10, opacity: 0 }}
                                                        animate={{ x: 0, opacity: 1 }}
                                                        transition={{ delay: 0.3 }}
                                                        className="font-bold text-white leading-tight"
                                                    >
                                                        {winner.username ? `@${winner.username}` : (winner.firstname || t(language, 'winnerFallback'))}
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
                                                className="flex items-center space-x-2 text-amber-500/60"
                                            >
                                                <Gift size={20} />
                                            </motion.div>
                                        </GlassCard>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>
                    </section>
                    <motion.footer
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center text-xs text-white/30 pt-4"
                    >
                        {t(language, 'congratsWinners')}
                    </motion.footer>
                </div>
            );
        }
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 px-6 text-center">
                <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center text-red-500">
                    <Trophy size={40} className="opacity-50" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-xl font-bold">{t(language, 'contestUnavailableTitle')}</h2>
                    <p className="text-sm text-white/40 italic">
                        {t(language, 'contestUnavailableText')}
                    </p>
                </div>
                <Button variant="secondary" onClick={() => tg.close()}>{t(language, 'close')}</Button>
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
                        <p className="text-sm text-white/60">{t(language, 'drawFinished')}</p>
                    </div>
                </header>

                <section className="space-y-4">
                    <div className="flex items-center justify-between px-1">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-white/40">
                            {t(language, 'winners')}
                        </h2>
                        {!drawComplete && (
                            <motion.div
                                animate={{ opacity: [0.4, 1, 0.4] }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                                className="text-xs text-primary font-medium"
                            >
                                {t(language, 'announcingResults')}
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
                                                    {winner.username ? `@${winner.username}` : (winner.firstname || t(language, 'winnerFallback'))}
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
                        <p className="text-xs text-white/30 mb-4">{t(language, 'congratsWinners')}</p>
                        <Button variant="secondary" onClick={() => tg.close()}>{t(language, 'close')}</Button>
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
                            <span>{liveParticipantsCount ?? contest.participants_count} {t(language, 'participants')}</span>
                        </div>
                        <button
                            type="button"
                            className="flex items-center space-x-1.5 hover:text-white transition-colors"
                            onClick={() => setPrizesOpen(true)}
                        >
                            <Trophy size={14} className="text-amber-400" />
                            <span>{contest.prize_count} {t(language, 'prizes')}</span>
                        </button>
                    </div>
                </div>
            </header>

            {contest.end_date && (
                <CountdownTimer endDate={contest.end_date} onEnd={handleCountdownEnd} language={language} />
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
                            <h3 className="text-xl font-bold text-emerald-400">{t(language, 'youParticipate')}</h3>
                            <p className="text-xs text-white/60">{t(language, 'allConditionsMet')}</p>
                        </div>
                        <Button variant="secondary" onClick={() => tg.close()}>{t(language, 'close')}</Button>
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
                            <h2 className="text-sm font-bold uppercase tracking-wider text-white/40 px-1">{t(language, 'conditionsTitle')}</h2>
                            {registerError && (
                                <GlassCard className="p-3 border border-red-500/30 bg-red-500/10 text-red-200 text-xs">
                                    {registerError}
                                </GlassCard>
                            )}
                            {pendingExternalAuth && (
                                <GlassCard className="p-4 border border-primary/30 bg-primary/10">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2 text-primary">
                                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
                                                <span className="text-xs font-bold uppercase tracking-[0.24em]">
                                                    {t(language, 'connectingAccount')}
                                                </span>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-sm font-semibold text-white">
                                                    {t(language, 'finishAuth', { service: pendingExternalAuth === 'instagram' ? 'Instagram' : pendingExternalAuth === 'youtube' ? 'YouTube' : 'TikTok' })}
                                                </p>
                                                <p className="text-xs text-white/60">
                                                    {t(language, 'autoCheckHint')}
                                                </p>
                                            </div>
                                        </div>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            className="shrink-0 px-3 py-2 text-xs"
                                            onClick={() => {
                                                setRegisterError(null);
                                                refetchStatus();
                                            }}
                                        >
                                            <RefreshCw size={14} className="mr-2" />
                                            {t(language, 'checkAgain')}
                                        </Button>
                                    </div>
                                    {pendingExternalCondition && !pendingExternalCondition.met && pendingExternalCondition.connected && (
                                        <div className="mt-3 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70">
                                            <ExternalLink size={14} className="text-primary" />
                                            {t(language, 'accountConnectedHint')}
                                        </div>
                                    )}
                                </GlassCard>
                            )}
                            <GlassCard className="p-2 space-y-2">
                                {status?.conditions.map((condition, idx) => (
                                    <ConditionItem
                                        key={idx}
                                        type={condition.type}
                                        label={condition.title}
                                        isMet={condition.met}
                                        isConnected={condition.connected}
                                        statusText={getConditionStatusText(condition)}
                                        actionLabel={
                                            condition.type === 'instagram'
                                                ? `${condition.connected ? t(language, 'open') : t(language, 'connect')} Instagram`
                                                : condition.type === 'youtube'
                                                    ? `${condition.connected ? t(language, 'open') : t(language, 'connect')} YouTube`
                                                    : condition.type === 'tiktok'
                                                        ? `${condition.connected ? t(language, 'open') : t(language, 'connect')} TikTok`
                                                        : undefined
                                        }
                                        onAction={() => handleConditionAction(condition)}
                                    />
                                ))}
                                {(!status || status.conditions.length === 0) && (
                                    <p className="p-4 text-center text-white/40 text-sm">{t(language, 'noConditions')}</p>
                                )}
                            </GlassCard>
                            {contest.require_captcha && status?.external_conditions_met && !status?.is_registered && (
                                <GlassCard className="p-4 border border-cyan-500/20 bg-cyan-500/5 space-y-3">
                                    <div className="flex items-start gap-3">
                                        <div className="rounded-xl bg-cyan-500/15 p-2 text-cyan-300">
                                            <ShieldCheck size={18} />
                                        </div>
                                        <div className="flex-1 space-y-1">
                                            <div className="text-sm font-bold text-white">{t(language, 'captchaTitle')}</div>
                                            <div className="text-xs text-white/50">{t(language, 'captchaHint')}</div>
                                        </div>
                                    </div>
                                    <div className="grid grid-cols-[1fr_1.4fr] gap-2">
                                        <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-center text-lg font-black text-cyan-200">
                                            {captchaChallenge?.question || '...'}
                                        </div>
                                        <input
                                            inputMode="numeric"
                                            value={captchaAnswer}
                                            onChange={(event) => setCaptchaAnswer(event.target.value.replace(/[^\d-]/g, ''))}
                                            placeholder={t(language, 'captchaAnswer')}
                                            className="form-input"
                                        />
                                    </div>
                                    <div className="grid grid-cols-[1fr_auto] gap-2">
                                        <Button
                                            type="button"
                                            onClick={handleCaptchaRegister}
                                            disabled={!captchaAnswer.trim() || isRegistering || !captchaChallenge}
                                            isLoading={isRegistering}
                                        >
                                            {t(language, 'register')}
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            onClick={() => {
                                                setCaptchaAnswer('');
                                                refetchCaptcha();
                                            }}
                                            disabled={isRegistering}
                                            className="px-3"
                                        >
                                            <RefreshCw size={16} />
                                        </Button>
                                    </div>
                                </GlassCard>
                            )}
                        </section>

                        <footer className="pt-2">
                            <GlassCard className="bg-primary/5 border-primary/20 p-4">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center space-x-2 text-white/80">
                                        <Clock size={16} className="text-primary" />
                                        <span className="text-sm font-medium">{t(language, 'drawDate')}: {new Date(contest.end_date).toLocaleDateString()}</span>
                                    </div>
                                    <div className="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded">{t(language, 'active')}</div>
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
                                        {status?.can_register ? t(language, 'preparingRegistration') : t(language, 'completeConditions')}
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
                                <span className="text-sm font-bold">{t(language, 'contestPrizes')}</span>
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
                                <p className="text-white/40 text-sm">{t(language, 'prizesNotConfigured')}</p>
                            )}
                        </div>
                        <div className="p-4 border-t border-white/10">
                            <Button variant="secondary" className="w-full" onClick={() => setPrizesOpen(false)}>{t(language, 'close')}</Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
