import React from 'react';
import { motion } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { GlassCard } from '../ui/Cards';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface JournalAction {
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

interface JournalContest {
    id: number;
}

interface JournalTabProps {
    recentActions?: JournalAction[];
    filteredRecentActions: JournalAction[];
    actionSearch: string;
    actionFilter: 'all' | 'contest' | 'channel' | 'youtube_channel' | 'tiktok_channel';
    onActionSearchChange: (value: string) => void;
    onActionFilterChange: (value: 'all' | 'contest' | 'channel' | 'youtube_channel' | 'tiktok_channel') => void;
    historyActionLabels: Record<string, string>;
    formatHistoryDetails: (entry: JournalAction) => string | null;
    contests?: JournalContest[];
    onOpenContest: (contestId: number) => void;
}

export const JournalTab: React.FC<JournalTabProps> = ({
    recentActions,
    filteredRecentActions,
    actionSearch,
    actionFilter,
    onActionSearchChange,
    onActionFilterChange,
    historyActionLabels,
    formatHistoryDetails,
    contests,
    onOpenContest,
}) => {
    return (
        <motion.div
            key="journal"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
        >
            <div className="flex items-center justify-between px-1">
                <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Журнал действий</h3>
                <div className="text-[10px] text-white/30">{filteredRecentActions.length} из {recentActions?.length || 0}</div>
            </div>

            <GlassCard className="p-4 border-white/5 space-y-3">
                <input
                    type="text"
                    value={actionSearch}
                    onChange={(e) => onActionSearchChange(e.target.value)}
                    placeholder="Поиск по журналу действий"
                    className="form-input"
                />
                <div className="flex flex-wrap gap-2">
                    {[
                        { id: 'all', label: 'Все' },
                        { id: 'contest', label: 'Конкурсы' },
                        { id: 'channel', label: 'Telegram' },
                        { id: 'youtube_channel', label: 'YouTube' },
                        { id: 'tiktok_channel', label: 'TikTok' },
                    ].map((filter) => (
                        <button
                            key={filter.id}
                            onClick={() => onActionFilterChange(filter.id as 'all' | 'contest' | 'channel' | 'youtube_channel' | 'tiktok_channel')}
                            className={cn(
                                'px-3 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-colors',
                                actionFilter === filter.id
                                    ? 'bg-primary text-white'
                                    : 'bg-white/5 text-white/55 hover:bg-white/10'
                            )}
                        >
                            {filter.label}
                        </button>
                    ))}
                </div>
            </GlassCard>

            {recentActions && recentActions.length > 0 ? (
                <div className="space-y-3">
                    {filteredRecentActions.map((entry) => (
                        <GlassCard key={entry.id} className="p-4 border-white/5">
                            <div className="flex items-start justify-between gap-3 text-xs">
                                <div className="min-w-0">
                                    <div className="font-semibold text-white/85">
                                        {historyActionLabels[entry.action_type] || entry.action_type}
                                    </div>
                                    {entry.contest_title && (
                                        <div className="text-white/50 truncate">{entry.contest_title}</div>
                                    )}
                                    {formatHistoryDetails(entry) && (
                                        <div className="text-white/35 mt-1">{formatHistoryDetails(entry)}</div>
                                    )}
                                    {entry.target_type === 'contest' && entry.target_id && contests?.some((contest) => contest.id === Number(entry.target_id)) && (
                                        <button
                                            onClick={() => onOpenContest(Number(entry.target_id))}
                                            className="mt-3 px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-colors"
                                        >
                                            Открыть конкурс
                                        </button>
                                    )}
                                </div>
                                <div className="shrink-0 text-white/25">
                                    {new Date(entry.created_at).toLocaleString()}
                                </div>
                            </div>
                        </GlassCard>
                    ))}
                </div>
            ) : (
                <GlassCard className="p-8 border-white/5 text-center text-sm text-white/35">
                    Действий пока нет.
                </GlassCard>
            )}

            {recentActions && recentActions.length > 0 && filteredRecentActions.length === 0 && (
                <GlassCard className="p-6 border-white/5 text-center text-xs text-white/40">
                    По текущему фильтру записи не найдены.
                </GlassCard>
            )}
        </motion.div>
    );
};
