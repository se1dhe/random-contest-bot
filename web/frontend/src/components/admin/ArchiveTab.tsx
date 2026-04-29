import React from 'react';
import { motion } from 'framer-motion';
import { GlassCard } from '../ui/Cards';
import { Button } from '../ui/Button';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ArchiveContest {
    id: number;
    title: string;
    status: string;
    publish_at?: string | null;
    prize_count: number;
    end_date: string;
    channel?: { channel_title?: string };
}

interface ArchiveTabProps {
    archivedContests: ArchiveContest[];
    effectiveStatus: (contest: ArchiveContest) => string;
    onOpenContest: (contestId: number) => void;
}

export const ArchiveTab: React.FC<ArchiveTabProps> = ({
    archivedContests,
    effectiveStatus,
    onOpenContest,
}) => {
    return (
        <motion.div
            key="archive"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
        >
            <div className="flex items-center justify-between px-1">
                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Архив конкурсов</h3>
                <div className="text-[10px] text-white/30">{archivedContests.length} записей</div>
            </div>

            {archivedContests.length > 0 ? (
                <div className="space-y-3">
                    {archivedContests
                        .slice()
                        .sort((left, right) => new Date(right.end_date).getTime() - new Date(left.end_date).getTime())
                        .map((contest) => (
                            <GlassCard
                                key={contest.id}
                                className="p-4 border-white/5 hover:border-white/15 transition-all"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="font-semibold text-sm text-white/90 truncate">{contest.title}</div>
                                        <div className="text-[11px] text-white/45 truncate">
                                            {contest.channel?.channel_title || 'Без канала'}
                                        </div>
                                    </div>
                                    <div className="text-[10px] text-white/35 shrink-0">
                                        {new Date(contest.end_date).toLocaleString()}
                                    </div>
                                </div>
                                <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
                                    <div className={cn(
                                        'text-[8px] font-black tracking-widest px-2 py-1 rounded-md uppercase',
                                        effectiveStatus(contest) === 'results_published'
                                            ? 'bg-white/5 text-white/50 border border-white/10'
                                            : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                                    )}>
                                        {effectiveStatus(contest)}
                                    </div>
                                    <Button variant="secondary" onClick={() => onOpenContest(contest.id)}>
                                        Открыть
                                    </Button>
                                </div>
                            </GlassCard>
                        ))}
                </div>
            ) : (
                <GlassCard className="p-8 border-white/5 text-center text-sm text-white/35">
                    Завершённых конкурсов пока нет.
                </GlassCard>
            )}
        </motion.div>
    );
};
