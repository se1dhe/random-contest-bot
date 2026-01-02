import React, { useState, useEffect, memo } from 'react';
import { Timer } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from './Cards';

interface CountdownTimerProps {
    endDate: string;
    onEnd?: () => void;
}

// Memoized unit component to prevent unnecessary re-renders
const TimeUnit = memo(({ value, label }: { value: number, label: string }) => (
    <div className="flex flex-col items-center">
        <div className="relative h-7 w-8 flex items-center justify-center">
            <AnimatePresence initial={false} mode="popLayout">
                <motion.span
                    key={value}
                    initial={{ y: 15, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: -15, opacity: 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="text-xl font-bold font-mono leading-none tabular-nums"
                >
                    {value.toString().padStart(2, '0')}
                </motion.span>
            </AnimatePresence>
        </div>
        <span className="text-[10px] uppercase opacity-50 font-medium mt-0.5">{label}</span>
    </div>
));

TimeUnit.displayName = 'TimeUnit';

export const CountdownTimer: React.FC<CountdownTimerProps> = ({ endDate, onEnd }) => {
    const [timeLeft, setTimeLeft] = useState<{
        days: number;
        hours: number;
        minutes: number;
        seconds: number;
        isExpired: boolean;
    } | null>(null);

    useEffect(() => {
        const calculateTimeLeft = () => {
            const difference = +new Date(endDate) - +new Date();

            if (difference > 0) {
                setTimeLeft({
                    days: Math.floor(difference / (1000 * 60 * 60 * 24)),
                    hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
                    minutes: Math.floor((difference / 1000 / 60) % 60),
                    seconds: Math.floor((difference / 1000) % 60),
                    isExpired: false
                });
            } else {
                setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true });
                if (onEnd) onEnd();
            }
        };

        calculateTimeLeft();
        const timer = setInterval(calculateTimeLeft, 1000);

        return () => clearInterval(timer);
    }, [endDate, onEnd]);

    if (!timeLeft) return null;

    if (timeLeft.isExpired) {
        return (
            <GlassCard className="p-4 flex items-center justify-center border-red-500/20 bg-red-500/5">
                <div className="flex items-center gap-2 text-red-500 font-bold uppercase tracking-wider text-xs">
                    <Timer size={16} />
                    <span>Розыгрыш начался</span>
                </div>
            </GlassCard>
        );
    }

    return (
        <div className="glass-card p-4 flex items-center justify-between border-primary/20">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                    <Timer size={20} />
                </div>
                <div>
                    <h4 className="text-sm font-semibold opacity-80">До финала:</h4>
                    <p className="text-[11px] opacity-50">Живое обновление</p>
                </div>
            </div>

            <div className="flex gap-2">
                {timeLeft.days > 0 && (
                    <>
                        <TimeUnit value={timeLeft.days} label="дн" />
                        <span className="text-xl font-bold opacity-20 self-start mt-[-2px]">:</span>
                    </>
                )}
                <TimeUnit value={timeLeft.hours} label="ч" />
                <span className="text-xl font-bold opacity-20 self-start mt-[-2px]">:</span>
                <TimeUnit value={timeLeft.minutes} label="м" />
                <span className="text-xl font-bold opacity-20 self-start mt-[-2px]">:</span>
                <TimeUnit value={timeLeft.seconds} label="с" />
            </div>
        </div>
    );
};
