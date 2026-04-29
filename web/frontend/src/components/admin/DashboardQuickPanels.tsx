import React from 'react';
import { GlassCard } from '../ui/Cards';
import { Button } from '../ui/Button';

interface DashboardQuickPanelsProps {
    recentActionsCount: number;
    archivedContestsCount: number;
    onOpenJournal: () => void;
    onOpenArchive: () => void;
}

export const DashboardQuickPanels: React.FC<DashboardQuickPanelsProps> = ({
    recentActionsCount,
    archivedContestsCount,
    onOpenJournal,
    onOpenArchive,
}) => {
    return (
        <div className="grid grid-cols-1 gap-3">
            <GlassCard className="p-4 border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Журнал действий</h3>
                    <div className="text-[10px] text-white/30">{recentActionsCount}</div>
                </div>
                <p className="text-xs text-white/45">
                    Детальная история действий с поиском и фильтрами доступна в отдельной вкладке.
                </p>
                <Button variant="secondary" onClick={onOpenJournal} className="w-full">
                    Открыть журнал
                </Button>
            </GlassCard>

            <GlassCard className="p-4 border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Архив конкурсов</h3>
                    <div className="text-[10px] text-white/30">{archivedContestsCount}</div>
                </div>
                <p className="text-xs text-white/45">
                    Полный список завершённых конкурсов вынесен в отдельную вкладку архива.
                </p>
                <Button variant="secondary" onClick={onOpenArchive} className="w-full">
                    Открыть архив
                </Button>
            </GlassCard>
        </div>
    );
};
