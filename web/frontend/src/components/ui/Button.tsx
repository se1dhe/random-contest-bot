import { motion, type HTMLMotionProps } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ButtonProps extends HTMLMotionProps<'button'> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
    isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
    children,
    className,
    variant = 'primary',
    isLoading,
    ...props
}) => {
    const variants = {
        primary: 'bg-primary text-white shadow-lg shadow-primary/20 hover:bg-primary/90',
        secondary: 'bg-white/10 text-white hover:bg-white/20',
        outline: 'border border-white/10 text-white hover:bg-white/5',
        ghost: 'text-white hover:bg-white/5',
    };

    return (
        <motion.button
            whileTap={{ scale: 0.98 }}
            className={cn(
                'relative inline-flex items-center justify-center rounded-xl px-4 py-2.5 font-semibold transition-colors focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed',
                variants[variant],
                className
            )}
            {...props}
        >
            {isLoading ? (
                <div className="flex items-center space-x-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                    <span>Загрузка...</span>
                </div>
            ) : (
                children
            )}
        </motion.button>
    );
};
