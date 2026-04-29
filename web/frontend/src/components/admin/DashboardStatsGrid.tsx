import React from 'react';
import { Trophy, TrendingUp, Clock, AlertCircle, CheckCircle2 } from 'lucide-react';
import { GlassCard } from '../ui/Cards';

interface DashboardStatsGridProps {
    totalContests: number;
    activeContests: number;
    completedContests: number;
    scheduledCount: number;
    draftCount: number;
    archivedCount: number;
    onOpenAllContests: () => void;
    onOpenActiveContests: () => void;
    onOpenScheduledContests: () => void;
    onOpenDraftContests: () => void;
    onOpenArchive: () => void;
}

export const DashboardStatsGrid: React.FC<DashboardStatsGridProps> = ({
    totalContests,
    activeContests,
    completedContests,
    scheduledCount,
    draftCount,
    archivedCount,
    onOpenAllContests,
    onOpenActiveContests,
    onOpenScheduledContests,
    onOpenDraftContests,
    onOpenArchive,
}) => {
    const cardActionProps = (handler: () => void) => ({
        onClick: handler,
        role: 'button' as const,
        tabIndex: 0,
        onKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handler();
            }
        },
    });

    return (
        <div className="grid grid-cols-2 gap-3">
            <GlassCard
                {...cardActionProps(onOpenAllContests)}
                className="p-3 bg-primary/5 hover:bg-primary/10 transition-colors cursor-pointer active:scale-[0.99]"
            >
                <div className="flex items-center space-x-2 text-white/40 mb-1">
                    <Trophy size={14} />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Всего конкурсов</span>
                </div>
                <div className="text-2xl font-bold">{totalContests}</div>
            </GlassCard>
            <GlassCard
                {...cardActionProps(onOpenActiveContests)}
                className="p-3 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors cursor-pointer active:scale-[0.99]"
            >
                <div className="flex items-center space-x-2 text-emerald-400/40 mb-1">
                    <TrendingUp size={14} />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Активные</span>
                </div>
                <div className="text-2xl font-bold flex items-baseline">
                    {activeContests}
                    <span className="text-[10px] ml-1 text-emerald-400">/ {completedContests}</span>
                </div>
            </GlassCard>
            <GlassCard
                {...cardActionProps(onOpenScheduledContests)}
                className="p-3 bg-sky-500/5 hover:bg-sky-500/10 transition-colors cursor-pointer active:scale-[0.99]"
            >
                <div className="flex items-center space-x-2 text-sky-300/50 mb-1">
                    <Clock size={14} />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Запланированы</span>
                </div>
                <div className="text-2xl font-bold">{scheduledCount}</div>
            </GlassCard>
            <GlassCard
                {...cardActionProps(onOpenDraftContests)}
                className="p-3 bg-amber-500/5 hover:bg-amber-500/10 transition-colors cursor-pointer active:scale-[0.99]"
            >
                <div className="flex items-center space-x-2 text-amber-300/50 mb-1">
                    <AlertCircle size={14} />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Черновики</span>
                </div>
                <div className="text-2xl font-bold">{draftCount}</div>
            </GlassCard>
            <GlassCard
                {...cardActionProps(onOpenArchive)}
                className="p-3 bg-white/5 hover:bg-white/10 transition-colors cursor-pointer active:scale-[0.99]"
            >
                <div className="flex items-center space-x-2 text-white/40 mb-1">
                    <CheckCircle2 size={14} />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Архив</span>
                </div>
                <div className="text-2xl font-bold">{archivedCount}</div>
            </GlassCard>
        </div>
    );
};
