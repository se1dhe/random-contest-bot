import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    const location = useLocation();

    return (
        <div className="min-h-screen flex flex-col max-w-lg mx-auto overflow-hidden">
            <AnimatePresence mode="wait">
                <motion.main
                    key={location.pathname}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3, ease: 'easeOut' }}
                    className="flex-1 px-4 py-6"
                >
                    {children}
                </motion.main>
            </AnimatePresence>

            <footer className="py-4 text-center text-sm text-gray-500">
                developed by{' '}
                <a
                    href="https://t.me/se1dhe"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:text-primary/80 transition-colors bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500 font-medium"
                >
                    se1dhe
                </a>{' '}
                with <span className="text-red-500 animate-pulse">❤️</span>
            </footer>
        </div>
    );
};
