import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import {
    ImageIcon,
    Plus,
    Trash2,
    ChevronLeft,
    ChevronRight,
    Youtube
} from 'lucide-react';
import { Button } from './ui/Button';
import { GlassCard } from './ui/Cards';
import { useTelegram } from '../hooks/useTelegram';

interface Prize {
    place: number;
    title: string;
    description: string;
}

interface Sponsor {
    channel_id: string;
    channel_title: string;
}

interface ContestFormProps {
    onSuccess: () => void;
    onCancel: () => void;
}

export const ContestForm: React.FC<ContestFormProps> = ({ onSuccess, onCancel }) => {
    const { initData, hapticFeedback } = useTelegram();
    const [step, setStep] = useState(1);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Form State
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [channelId, setChannelId] = useState('');
    const [endDate, setEndDate] = useState('');
    const [prizeCount, setPrizeCount] = useState(1);
    const [drawMethod, setDrawMethod] = useState('random');
    const [prizes, setPrizes] = useState<Prize[]>([{ place: 1, title: '', description: '' }]);
    const [sponsors, setSponsors] = useState<Sponsor[]>([]); // Initialize properly
    const [requireYoutube, setRequireYoutube] = useState(false);
    const [youtubeDays, setYoutubeDays] = useState(0);
    const [image, setImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);

    // New Fields
    const [youtubeChannelId, setYoutubeChannelId] = useState('');


    // Queries
    const { data: channels } = useQuery<any[]>({
        queryKey: ['admin_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData,
    });

    const { data: youtubeChannels } = useQuery<any[]>({
        queryKey: ['admin_youtube_channels', initData],
        queryFn: async () => {
            const res = await axios.get('/api/admin/youtube-channels', {
                headers: { '_auth': initData },
                params: { _auth: initData }
            });
            return res.data;
        },
        enabled: !!initData,
    });

    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setImage(file);
            const reader = new FileReader();
            reader.onloadend = () => setImagePreview(reader.result as string);
            reader.readAsDataURL(file);
        }
    };

    const toggleSponsor = (ch: any) => {
        if (sponsors.find(s => s.channel_id === ch.channel_id)) {
            setSponsors(sponsors.filter(s => s.channel_id !== ch.channel_id));
        } else {
            setSponsors([...sponsors, { channel_id: ch.channel_id, channel_title: ch.channel_title }]);
        }
    };

    const handleAddPrize = () => {
        const nextPlace = prizes.length + 1;
        setPrizes([...prizes, { place: nextPlace, title: '', description: '' }]);
        setPrizeCount(nextPlace);
    };

    const handleRemovePrize = (idx: number) => {
        const newPrizes = prizes.filter((_, i) => i !== idx).map((p, i) => ({ ...p, place: i + 1 }));
        setPrizes(newPrizes);
        setPrizeCount(newPrizes.length);
    };

    const updatePrize = (idx: number, field: keyof Prize, value: any) => {
        const newPrizes = [...prizes];
        newPrizes[idx] = { ...newPrizes[idx], [field]: value };
        setPrizes(newPrizes);
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        hapticFeedback('medium');

        const formData = new FormData();
        formData.append('title', title);
        formData.append('description', description);
        formData.append('channel_id', channelId);
        formData.append('end_date', endDate);
        formData.append('prize_count', prizeCount.toString());
        formData.append('draw_method', drawMethod);
        formData.append('require_youtube_subscription', requireYoutube.toString());
        formData.append('youtube_subscription_days_required', youtubeDays.toString());
        formData.append('prizes', JSON.stringify(prizes));
        formData.append('sponsors', JSON.stringify(sponsors));
        if (requireYoutube) formData.append('youtube_channel_id', youtubeChannelId);
        if (image) formData.append('image', image);

        try {
            await axios.post('/api/admin/contests', formData, {
                headers: {
                    '_auth': initData,
                    'Content-Type': 'multipart/form-data'
                },
                params: { _auth: initData } // Backend might expect it here too
            });
            hapticFeedback('heavy');
            onSuccess();
        } catch (err) {
            console.error('Failed to create contest', err);
            hapticFeedback('rigid');
        } finally {
            setIsSubmitting(false);
        }
    };

    const nextStep = () => {
        hapticFeedback('light');
        setStep(s => s + 1);
    };

    const prevStep = () => {
        hapticFeedback('light');
        setStep(s => s - 1);
    };

    return (
        <div className="space-y-6">
            <header className="flex items-center space-x-3">
                <button onClick={onCancel} className="p-2 bg-white/5 rounded-full text-white/40">
                    <ChevronLeft size={20} />
                </button>
                <h2 className="text-xl font-bold">Новый конкурс</h2>
            </header>

            {/* Progress Bar */}
            <div className="flex space-x-2 px-1">
                {[1, 2, 3].map(i => (
                    <div key={i} className={`h-1.5 flex-1 rounded-full transition-all ${i <= step ? 'bg-primary shadow-[0_0_8px_rgba(139,92,246,0.5)]' : 'bg-white/10'}`} />
                ))}
            </div>

            <AnimatePresence mode="wait">
                {step === 1 && (
                    <motion.div
                        key="step1"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className="space-y-5"
                    >
                        <div className="space-y-4">
                            <div>
                                <label className="form-label">Заголовок</label>
                                <input
                                    className="form-input"
                                    placeholder="Название вашего розыгрыша"
                                    value={title}
                                    onChange={e => setTitle(e.target.value)}
                                />
                            </div>

                            <div>
                                <label className="form-label">Описание (опционально)</label>
                                <textarea
                                    className="form-input min-h-[100px] py-3"
                                    placeholder="Расскажите о конкурсе..."
                                    value={description}
                                    onChange={e => setDescription(e.target.value)}
                                />
                            </div>

                            <div>
                                <label className="form-label">Канал проведения</label>
                                <select
                                    className="form-select"
                                    value={channelId}
                                    onChange={e => setChannelId(e.target.value)}
                                >
                                    <option value="">Выберите канал...</option>
                                    {channels?.map(c => (
                                        <option key={c.channel_id} value={c.channel_id}>{c.channel_title}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="form-label">Дата окончания</label>
                                    <input
                                        type="datetime-local"
                                        className="form-input"
                                        value={endDate}
                                        onChange={e => setEndDate(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="form-label">Метод выбора</label>
                                    <select
                                        className="form-select"
                                        value={drawMethod}
                                        onChange={e => setDrawMethod(e.target.value)}
                                    >
                                        <option value="random">Случайно</option>
                                        <option value="by_activity">По активности</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <Button onClick={nextStep} disabled={!title || !channelId || !endDate} className="w-full">
                            Далее <ChevronRight size={18} className="ml-1" />
                        </Button>
                    </motion.div>
                )}

                {step === 2 && (
                    <motion.div
                        key="step2"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className="space-y-6"
                    >
                        <div className="space-y-4">
                            <div className="flex items-center justify-between px-1">
                                <label className="form-label mb-0">Призовые места</label>
                                <span className="text-[10px] text-primary font-bold">{prizes.length} МЕСТ</span>
                            </div>

                            <div className="space-y-3">
                                {prizes.map((prize, idx) => (
                                    <GlassCard key={idx} className="p-4 space-y-3 relative overflow-hidden">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-2">
                                                <div className="w-6 h-6 bg-primary/20 rounded-full flex items-center justify-center text-primary text-[10px] font-black">
                                                    {prize.place}
                                                </div>
                                                <span className="text-[10px] font-bold text-white/60">МЕСТО</span>
                                            </div>
                                            {prizes.length > 1 && (
                                                <button onClick={() => handleRemovePrize(idx)} className="text-red-400/50 hover:text-red-400">
                                                    <Trash2 size={16} />
                                                </button>
                                            )}
                                        </div>
                                        <input
                                            className="form-input text-xs py-2"
                                            placeholder="Название приза"
                                            value={prize.title}
                                            onChange={e => updatePrize(idx, 'title', e.target.value)}
                                        />
                                        <textarea
                                            className="form-input text-xs py-2 min-h-[60px]"
                                            placeholder="Описание приза (опционально)"
                                            value={prize.description}
                                            onChange={e => updatePrize(idx, 'description', e.target.value)}
                                        />
                                    </GlassCard>
                                ))}
                            </div>

                            <button
                                onClick={handleAddPrize}
                                className="w-full py-3 border border-dashed border-white/10 rounded-xl flex items-center justify-center text-white/40 hover:text-white/60 hover:bg-white/5 transition-all text-sm font-medium"
                            >
                                <Plus size={18} className="mr-2" /> Добавить место
                            </button>
                        </div>

                        <div className="flex space-x-3">
                            <Button variant="secondary" onClick={prevStep} className="flex-1">Назад</Button>
                            <Button onClick={nextStep} disabled={prizes.some(p => !p.title)} className="flex-[2]">Далее</Button>
                        </div>
                    </motion.div>
                )}

                {step === 3 && (
                    <motion.div
                        key="step3"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className="space-y-6"
                    >
                        <div className="space-y-6">
                            {/* Image Upload */}
                            <div className="space-y-3">
                                <label className="form-label">Обложка конкурса</label>
                                <div
                                    className="relative aspect-video rounded-2xl border-2 border-dashed border-white/10 overflow-hidden group cursor-pointer"
                                    onClick={() => document.getElementById('image-upload')?.click()}
                                >
                                    {imagePreview ? (
                                        <img src={imagePreview} className="w-full h-full object-cover" />
                                    ) : (
                                        <div className="w-full h-full flex flex-col items-center justify-center text-white/20 space-y-2">
                                            <ImageIcon size={32} />
                                            <span className="text-xs font-medium">Кликните для выбора фото</span>
                                        </div>
                                    )}
                                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                        <span className="text-xs font-bold text-white uppercase tracking-widest">Изменить</span>
                                    </div>
                                    <input type="file" id="image-upload" className="hidden" accept="image/*" onChange={handleImageChange} />
                                </div>
                            </div>

                            {/* Sponsors Selection */}
                            <div className="space-y-3">
                                <label className="form-label">Спонсоры (каналы для обязательной подписки)</label>
                                <div className="space-y-2">
                                    {channels?.filter(c => String(c.channel_id) !== channelId).map(ch => {
                                        const isSelected = sponsors.some(s => s.channel_id === ch.channel_id);
                                        return (
                                            <GlassCard
                                                key={ch.channel_id}
                                                onClick={() => toggleSponsor(ch)}
                                                className={`p-3 flex items-center space-x-3 cursor-pointer transition-all ${isSelected ? 'border-primary/50 bg-primary/10' : 'border-white/5 opacity-60 hover:opacity-100'}`}
                                            >
                                                <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-colors ${isSelected ? 'bg-primary border-primary' : 'border-white/20'}`}>
                                                    {isSelected && <Plus size={14} className="text-white" />}
                                                </div>
                                                <span className="text-sm font-medium">{ch.channel_title}</span>
                                            </GlassCard>
                                        );
                                    })}
                                    {channels?.filter(c => String(c.channel_id) !== channelId).length === 0 && (
                                        <p className="text-[10px] text-white/20 italic">Нет доступных каналов для спонсорства</p>
                                    )}
                                </div>
                            </div>

                            {/* YouTube Condition */}
                            <div className="space-y-3">
                                <label className="form-label">Условие YouTube</label>
                                <GlassCard className={`p-4 transition-all ${requireYoutube ? 'border-red-500/20 bg-red-500/5' : ''}`}>
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center space-x-3">
                                            <div className={`p-2 rounded-lg ${requireYoutube ? 'bg-red-500/20 text-red-500' : 'bg-white/10 text-white/40'}`}>
                                                <Youtube size={20} />
                                            </div>
                                            <div>
                                                <div className="text-sm font-bold">Подписка на YouTube</div>
                                                <div className="text-[10px] text-white/40">Требовать от участников</div>
                                            </div>
                                        </div>
                                        <div
                                            className={`w-12 h-6 rounded-full p-1 cursor-pointer transition-colors ${requireYoutube ? 'bg-red-500' : 'bg-white/20'}`}
                                            onClick={() => setRequireYoutube(!requireYoutube)}
                                        >
                                            <motion.div
                                                animate={{ x: requireYoutube ? 24 : 0 }}
                                                className="w-4 h-4 bg-white rounded-full shadow-lg"
                                            />
                                        </div>
                                    </div>

                                    {requireYoutube && (
                                        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="pt-2 border-t border-white/5 space-y-3">
                                            <div>
                                                <label className="form-label text-[10px]">YouTube Канал</label>
                                                <select
                                                    className="form-select text-xs py-2 bg-red-500/5 border-red-500/20 focus:border-red-500/40"
                                                    value={youtubeChannelId}
                                                    onChange={e => setYoutubeChannelId(e.target.value)}
                                                >
                                                    <option value="">Выберите канал...</option>
                                                    {youtubeChannels?.map(c => (
                                                        <option key={c.channel_id} value={c.channel_id}>{c.title}</option>
                                                    ))}
                                                </select>
                                                {!youtubeChannels?.length && (
                                                    <div className="mt-1 text-[8px] text-red-400">Сначала добавьте каналы в настройках</div>
                                                )}
                                            </div>
                                            <div>
                                                <label className="form-label text-[10px]">Минимум дней подписки (0 - для новых)</label>
                                                <input
                                                    type="number"
                                                    className="form-input py-2 text-xs"
                                                    value={youtubeDays}
                                                    onChange={e => setYoutubeDays(parseInt(e.target.value) || 0)}
                                                />
                                            </div>
                                        </motion.div>
                                    )}
                                </GlassCard>
                            </div>
                        </div>

                        <div className="flex space-x-3">
                            <Button variant="secondary" onClick={prevStep} className="flex-1" disabled={isSubmitting}>Назад</Button>
                            <Button onClick={handleSubmit} isLoading={isSubmitting} className="flex-[2]">Создать конкурс</Button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div >
    );
};
