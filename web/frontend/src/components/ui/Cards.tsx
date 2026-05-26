import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { CheckCircle2, ExternalLink, Music2, Youtube } from 'lucide-react';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export const GlassCard: React.FC<HTMLMotionProps<'div'>> = ({
    children,
    className,
    ...props
}) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn('glass-card', className)}
        {...props}
    >
        {children}
    </motion.div>
);

interface ConditionItemProps {
    type: 'telegram' | 'youtube' | 'tiktok';
    label: string;
    isMet: boolean;
    isConnected?: boolean;
    statusText?: string;
    onAction: () => void;
    actionLabel?: string;
}

export const ConditionItem: React.FC<ConditionItemProps> = ({
    type,
    label,
    isMet,
    isConnected,
    statusText,
    onAction,
    actionLabel,
}) => {
    const iconTone = type === 'telegram'
        ? 'bg-blue-500/20 text-blue-400'
        : type === 'youtube'
            ? 'bg-red-500/20 text-red-400'
            : 'bg-slate-500/20 text-white/80';

    const actionText = actionLabel || (
        type === 'telegram'
            ? 'Подписаться'
            : isConnected
                ? 'Открыть'
                : 'Привязать'
    );
    const resolvedStatusText = statusText || (
        isMet
            ? 'Выполнено'
            : (type === 'telegram'
                ? 'Нужна подписка'
                : (isConnected ? 'Нужно подтвердить условие' : 'Аккаунт не подключен'))
    );

    return (
        <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center space-x-3">
                <div className={cn(
                    'p-2 rounded-lg',
                    iconTone
                )}>
                    {type === 'telegram' && <ExternalLink size={18} />}
                    {type === 'youtube' && <Youtube size={18} />}
                    {type === 'tiktok' && <Music2 size={18} />}
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-medium text-white/90 line-clamp-1">{label}</span>
                    <span className={cn('text-[10px] uppercase tracking-wider font-bold', isMet ? 'text-emerald-400' : 'text-white/40')}>
                        {resolvedStatusText}
                    </span>
                </div>
            </div>

            {!isMet && (
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                    onAction();
                    }}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-semibold transition-all active:scale-95"
                >
                    {actionText}
                </button>
            )}

            {isMet && (
                <div className="text-emerald-400">
                    <CheckCircle2 size={20} />
                </div>
            )}
        </div>
    );
};
