import React from 'react';
import { Database, Radio, Bot, Activity, AlertTriangle, CheckCircle2, Clock3, Trophy, Wrench, ArrowRight } from 'lucide-react';
import { GlassCard } from '../ui/Cards';

type HealthStatus = 'ok' | 'warning' | 'error' | 'disabled';

interface HealthService {
    status: HealthStatus;
    detail: string;
    public_url?: string | null;
    configured_domain?: string | null;
}

interface SystemHealthData {
    generated_at: string;
    services: {
        database: HealthService;
        redis: HealthService;
        bot_api: HealthService;
        ngrok: HealthService;
    };
    issues: {
        active_without_message_id: number;
        results_without_message_id: number;
        overdue_scheduled: number;
        finished_without_winners: number;
        total: number;
    };
    problematic_contests: Array<{
        contest_id: number;
        title: string;
        status: string;
        channel_title?: string | null;
        issue_type: string;
        detail: string;
        actionability: 'auto_repairable' | 'manual_attention';
    }>;
}

interface SystemHealthPanelProps {
    health?: SystemHealthData;
    onOpenContest?: (contestId: number) => void;
}

const statusTone = (status: HealthStatus) => {
    switch (status) {
        case 'ok':
            return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300';
        case 'warning':
            return 'border-amber-500/20 bg-amber-500/10 text-amber-300';
        case 'error':
            return 'border-red-500/20 bg-red-500/10 text-red-300';
        default:
            return 'border-white/10 bg-white/5 text-white/50';
    }
};

const statusLabel = (status: HealthStatus) => {
    switch (status) {
        case 'ok':
            return 'OK';
        case 'warning':
            return 'Внимание';
        case 'error':
            return 'Ошибка';
        default:
            return 'Отключено';
    }
};

export const SystemHealthPanel: React.FC<SystemHealthPanelProps> = ({ health, onOpenContest }) => {
    const services = [
        { key: 'database', label: 'PostgreSQL', icon: Database, data: health?.services.database },
        { key: 'redis', label: 'Redis', icon: Radio, data: health?.services.redis },
        { key: 'bot_api', label: 'Bot API', icon: Bot, data: health?.services.bot_api },
        { key: 'ngrok', label: 'Ngrok', icon: Activity, data: health?.services.ngrok },
    ] as const;

    const issues = [
        {
            key: 'active_without_message_id',
            label: 'Active без поста',
            value: health?.issues.active_without_message_id || 0,
            icon: AlertTriangle,
        },
        {
            key: 'results_without_message_id',
            label: 'Результаты без поста',
            value: health?.issues.results_without_message_id || 0,
            icon: CheckCircle2,
        },
        {
            key: 'overdue_scheduled',
            label: 'Просроченные scheduled',
            value: health?.issues.overdue_scheduled || 0,
            icon: Clock3,
        },
        {
            key: 'finished_without_winners',
            label: 'Finished без победителей',
            value: health?.issues.finished_without_winners || 0,
            icon: Trophy,
        },
    ];

    return (
        <GlassCard className="p-4 border-white/5 space-y-4">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Состояние системы</h3>
                    <p className="mt-1 text-xs text-white/45">
                        Живой статус сервисов и быстрый срез по проблемным конкурсам.
                    </p>
                </div>
                <div className="text-right">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-white/30">Проблем всего</div>
                    <div className="text-xl font-black text-white">{health?.issues.total || 0}</div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {services.map((service) => {
                    const Icon = service.icon;
                    const data = service.data;
                    return (
                        <div
                            key={service.key}
                            className={`rounded-2xl border p-3 ${statusTone(data?.status || 'disabled')}`}
                        >
                            <div className="flex items-center justify-between gap-3">
                                <div className="flex items-center gap-2">
                                    <Icon size={14} />
                                    <span className="text-xs font-bold uppercase tracking-wider">{service.label}</span>
                                </div>
                                <span className="text-[10px] font-black uppercase tracking-[0.2em]">
                                    {statusLabel(data?.status || 'disabled')}
                                </span>
                            </div>
                            <div className="mt-2 text-xs leading-relaxed opacity-90">
                                {data?.detail || 'Нет данных'}
                            </div>
                            {service.key === 'ngrok' && data?.public_url && (
                                <div className="mt-2 text-[11px] break-all text-white/70">
                                    {data.public_url}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            <div className="grid grid-cols-2 gap-2">
                {issues.map((issue) => {
                    const Icon = issue.icon;
                    return (
                        <div key={issue.key} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                            <div className="flex items-center justify-between gap-3">
                                <div className="flex items-center gap-2 text-white/45">
                                    <Icon size={14} />
                                    <span className="text-[10px] font-bold uppercase tracking-wider">{issue.label}</span>
                                </div>
                                <span className={`text-lg font-black ${issue.value > 0 ? 'text-amber-300' : 'text-white'}`}>
                                    {issue.value}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>

            {health?.problematic_contests?.length ? (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">Проблемные конкурсы</div>
                        <div className="text-[10px] text-white/30">
                            {health.problematic_contests.length} шт.
                        </div>
                    </div>
                    <div className="space-y-2">
                        {health.problematic_contests.map((contest) => (
                            <button
                                key={`${contest.issue_type}-${contest.contest_id}`}
                                type="button"
                                onClick={() => onOpenContest?.(contest.contest_id)}
                                className="w-full rounded-2xl border border-white/10 bg-white/5 p-3 text-left hover:bg-white/10 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="text-sm font-semibold text-white/90 truncate">{contest.title}</div>
                                        <div className="text-[11px] text-white/40 truncate">
                                            #{contest.contest_id} • {contest.channel_title || 'Без канала'} • {contest.status}
                                        </div>
                                    </div>
                                    <div className={`shrink-0 inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
                                        contest.actionability === 'auto_repairable'
                                            ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                                            : 'border-amber-500/20 bg-amber-500/10 text-amber-300'
                                    }`}>
                                        {contest.actionability === 'auto_repairable' ? <Wrench size={12} /> : <AlertTriangle size={12} />}
                                        {contest.actionability === 'auto_repairable' ? 'Автофикс' : 'Вручную'}
                                    </div>
                                </div>
                                <div className="mt-2 flex items-center justify-between gap-3">
                                    <div className="text-xs text-white/60">{contest.detail}</div>
                                    <div className="shrink-0 text-primary">
                                        <ArrowRight size={14} />
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            ) : null}

            <div className="text-[10px] text-white/30">
                Обновлено: {health ? new Date(health.generated_at).toLocaleString() : 'нет данных'}
            </div>
        </GlassCard>
    );
};
