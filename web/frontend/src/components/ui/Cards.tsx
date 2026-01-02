import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { CheckCircle2, ExternalLink, Youtube } from 'lucide-react';

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
    type: 'telegram' | 'youtube';
    label: string;
    isMet: boolean;
    isConnected?: boolean;
    onAction: () => void;
    actionLabel?: string;
}

export const ConditionItem: React.FC<ConditionItemProps> = ({
    type,
    label,
    isMet,
    isConnected,
    onAction,
    actionLabel,
}) => {
    return (
        <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center space-x-3">
                <div className={cn(
                    'p-2 rounded-lg',
                    type === 'telegram' ? 'bg-blue-500/20 text-blue-400' : 'bg-red-500/20 text-red-400'
                )}>
                    {type === 'telegram' ? <ExternalLink size={18} /> : <Youtube size={18} />}
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-medium text-white/90 line-clamp-1">{label}</span>
                    <span className={cn('text-[10px] uppercase tracking-wider font-bold', isMet ? 'text-emerald-400' : 'text-white/40')}>
                        {isMet ? 'Выполнено' : 'Нужна подписка'}
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
                    {actionLabel || (type === 'telegram' ? 'Подписаться' : (isConnected ? 'Подписаться' : 'Привязать'))}
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
