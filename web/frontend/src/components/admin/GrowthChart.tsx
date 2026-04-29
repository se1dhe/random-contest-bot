import React from 'react';
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface GrowthPoint {
    date: string;
    participants: number;
}

interface GrowthChartProps {
    data?: GrowthPoint[];
}

export const GrowthChart: React.FC<GrowthChartProps> = ({ data = [] }) => {
    const normalizedData = data.map((point) => ({
        ...point,
        participants: Number(point.participants) || 0,
    }));

    if (normalizedData.length === 0) {
        return (
            <div className="h-48 w-full rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center text-xs text-white/45">
                Пока нет данных для графика роста
            </div>
        );
    }

    return (
        <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={normalizedData}>
                    <defs>
                        <linearGradient id="colorPart" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                    <XAxis
                        dataKey="date"
                        stroke="#ffffff40"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1c1c1e', border: '1px solid #ffffff10', borderRadius: '8px' }}
                        itemStyle={{ color: '#fff' }}
                    />
                    <Area
                        type="monotone"
                        dataKey="participants"
                        stroke="#8b5cf6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorPart)"
                        dot={{ r: 3, strokeWidth: 2, fill: '#8b5cf6', stroke: '#1c1c1e' }}
                        activeDot={{ r: 5, strokeWidth: 0, fill: '#a78bfa' }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};
