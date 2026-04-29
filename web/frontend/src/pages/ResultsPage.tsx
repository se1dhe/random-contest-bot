import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import confetti from 'canvas-confetti';
import { GlassCard } from '../components/ui/Cards';
import { Trophy, Gift, Crown, Calendar, Users } from 'lucide-react';
import { useTelegram } from '../hooks/useTelegram';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { normalizeLanguage, t, type ContestLanguage } from '../i18n';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ResultInfo {
    contest_title: string;
    contest_description?: string;
    language?: ContestLanguage;
    image_url?: string | null;
    end_date: string;
    participants_count: number;
    winners: Array<{
        place: number;
        title: string;
        user_id: number;
        username: string;
        firstname: string | null;
    }>;
}

export const ResultsPage: React.FC = () => {
    const { contestId } = useParams();
    const { initData, userId } = useTelegram();
    const [revealedWinners, setRevealedWinners] = useState<number>(0);
    const [animationComplete, setAnimationComplete] = useState(false);

    const { data: results, isLoading } = useQuery<ResultInfo>({
        queryKey: ['results', contestId, initData, userId],
        queryFn: async () => {
            const res = await axios.get(`/api/contests/${contestId}/results-info`, {
                params: { user_id: userId, _auth: initData }
            });
            return res.data;
        },
        enabled: !!contestId && !!initData && !!userId,
    });

    // Winner reveal animation sequence
    useEffect(() => {
        if (!results || results.winners.length === 0 || animationComplete) return;

        const revealNextWinner = (index: number) => {
            if (index >= results.winners.length) {
                setAnimationComplete(true);
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

                revealNextWinner(index + 1);
            }, index === 0 ? 800 : 600); // Longer delay for first place
        };

        const timer = setTimeout(() => revealNextWinner(0), 500);
        return () => clearTimeout(timer);
    }, [results, animationComplete]);

    if (isLoading) {
        const language = 'ru';
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="spinner" />
                <p className="text-white/40 text-sm animate-pulse">{t(language, 'loadingResults')}</p>
            </div>
        );
    }

    if (!results) return null;
    const language = normalizeLanguage(results.language);

    return (
        <div className="space-y-6 pb-10">
            {/* Contest Header with Image */}
            <header className="space-y-4">
                {results.image_url ? (
                    <motion.img
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        src={results.image_url}
                        alt={results.contest_title}
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
                    <h1 className="text-2xl font-bold tracking-tight">{results.contest_title}</h1>

                    {/* Stats Row */}
                    <div className="flex items-center justify-center gap-4 text-sm text-white/60">
                        <div className="flex items-center gap-1.5">
                            <Calendar size={14} />
                            <span>{new Date(results.end_date).toLocaleDateString()}</span>
                        </div>
                        <div className="w-1 h-1 rounded-full bg-white/20" />
                        <div className="flex items-center gap-1.5">
                            <Users size={14} />
                            <span>{results.participants_count} {t(language, 'participants')}</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Winners Section */}
            <section className="space-y-4">
                <div className="flex items-center justify-between px-1">
                    <h2 className="text-sm font-bold uppercase tracking-wider text-white/40">
                        {t(language, 'winners')}
                    </h2>
                    {!animationComplete && (
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
                    {results.winners.length > 0 ? (
                        <AnimatePresence mode="popLayout">
                            {results.winners.slice(0, revealedWinners).map((winner, idx) => (
                                <motion.div
                                    key={idx}
                                    initial={{ scale: 0.8, opacity: 0, y: 20 }}
                                    animate={{ scale: 1, opacity: 1, y: 0 }}
                                    transition={{
                                        type: "spring",
                                        stiffness: 200,
                                        damping: 20
                                    }}
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
                    ) : (
                        <div className="text-center py-10 text-white/40 italic">
                            {t(language, 'winnersPending')}
                        </div>
                    )}
                </div>
            </section>

            {animationComplete && (
                <motion.footer
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center text-xs text-white/30 pt-4"
                >
                    {t(language, 'congratsWinners')}
                </motion.footer>
            )}
        </div>
    );
};
