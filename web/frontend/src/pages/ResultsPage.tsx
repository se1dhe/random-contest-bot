import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { motion } from 'framer-motion';
import { GlassCard } from '../components/ui/Cards';
import { Trophy, Gift, Crown, Calendar } from 'lucide-react';
import { useTelegram } from '../hooks/useTelegram';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ResultInfo {
    contest_title: string;
    end_date: string;
    winners: Array<{
        place: number;
        title: string;
        username: string;
        firstname: string | null;
    }>;
}

export const ResultsPage: React.FC = () => {
    const { contestId } = useParams();
    const { initData, userId } = useTelegram();

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

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
                <div className="spinner" />
                <p className="text-white/40 text-sm animate-pulse">Загружаем результаты...</p>
            </div>
        );
    }

    if (!results) return null;

    return (
        <div className="space-y-8 pb-10">
            <header className="text-center space-y-2">
                <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="inline-flex p-4 bg-amber-500/10 rounded-full text-amber-500 mb-2"
                >
                    <Trophy size={48} />
                </motion.div>
                <h1 className="text-3xl font-bold tracking-tight">{results.contest_title}</h1>
                <div className="flex items-center justify-center space-x-2 text-white/40 text-sm">
                    <Calendar size={14} />
                    <span>Завершено {new Date(results.end_date).toLocaleDateString()}</span>
                </div>
            </header>

            <section className="space-y-4">
                <h2 className="text-sm font-bold uppercase tracking-wider text-white/40 px-1">Наши победители</h2>
                <div className="space-y-3">
                    {results.winners.length > 0 ? (
                        results.winners.map((winner, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ x: -20, opacity: 0 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                className="relative overflow-hidden"
                            >
                                <GlassCard className={cn(
                                    'p-4 flex items-center justify-between',
                                    winner.place === 1 && 'bg-amber-500/5 border-amber-500/20 shadow-amber-500/10'
                                )}>
                                    <div className="flex items-center space-x-4">
                                        <div className={cn(
                                            'w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg',
                                            winner.place === 1 ? 'bg-amber-500 text-white' : 'bg-white/10 text-white/60'
                                        )}>
                                            {winner.place === 1 ? <Crown size={20} /> : winner.place}
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="font-bold text-white leading-tight">
                                                {winner.firstname || winner.username || 'Участник'}
                                            </span>
                                            <span className="text-xs text-white/40 truncate max-w-[150px]">
                                                Приз: {winner.title}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2 text-white/20">
                                        <Gift size={18} />
                                    </div>
                                </GlassCard>
                            </motion.div>
                        ))
                    ) : (
                        <div className="text-center py-10 text-white/40 italic">Победители пока не определены</div>
                    )}
                </div>
            </section>

            <footer className="text-center text-xs text-white/20 pt-4">
                Поздравляем всех победителей!
            </footer>
        </div>
    );
};
