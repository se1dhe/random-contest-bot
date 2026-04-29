import { useEffect } from 'react';
import WebApp from '@twa-dev/sdk';

export interface TelegramUser {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    language_code?: string;
    is_premium?: boolean;
}

export const useTelegram = () => {
    const user: TelegramUser | null = WebApp.initDataUnsafe.user ? (WebApp.initDataUnsafe.user as TelegramUser) : null;
    const startParam: string | null = WebApp.initDataUnsafe.start_param || null;

    useEffect(() => {
        WebApp.ready();
        WebApp.expand();

        // state initialized from WebApp.initDataUnsafe via lazy initializers
    }, []);

    const onClose = () => {
        WebApp.close();
    };

    const hapticFeedback = (type: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' = 'light') => {
        WebApp.HapticFeedback.impactOccurred(type);
    };

    const openLink = (url: string, options?: { try_instant_view?: boolean; try_browser?: string }) =>
        (WebApp.openLink as unknown as (target: string, opts?: { try_instant_view?: boolean; try_browser?: string }) => void)(url, options);
    const openTelegramLink = (url: string) => WebApp.openTelegramLink(url);

    return {
        onClose,
        tg: WebApp,
        user,
        startParam,
        hapticFeedback,
        openLink,
        openTelegramLink,
        initData: WebApp.initData,
        userId: WebApp.initDataUnsafe.user?.id,
    };
};
