import { useEffect, useState } from 'react';
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
    const [user, setUser] = useState<TelegramUser | null>(null);
    const [startParam, setStartParam] = useState<string | null>(null);

    useEffect(() => {
        WebApp.ready();
        WebApp.expand();

        if (WebApp.initDataUnsafe.user) {
            setUser(WebApp.initDataUnsafe.user as TelegramUser);
        }

        if (WebApp.initDataUnsafe.start_param) {
            setStartParam(WebApp.initDataUnsafe.start_param);
        }
    }, []);

    const onClose = () => {
        WebApp.close();
    };

    const hapticFeedback = (type: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft' = 'light') => {
        WebApp.HapticFeedback.impactOccurred(type);
    };

    const openLink = (url: string) => WebApp.openLink(url);
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
