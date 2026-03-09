// frontend/src/components/ProfitChart.tsx
import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

interface Props {
  data: any[];
  type?: 'area' | 'bar';
}

export function ProfitChart({ data, type = 'area' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[250px] text-gray-500">
        <div className="text-center">
          <div className="text-3xl mb-2">📊</div>
          <p className="text-sm">暂无数据</p>
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
          <p className="text-gray-400 text-xs">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p
              key={index}
              className={`text-sm font-bold ${
                entry.value >= 0 ? 'text-green-400' : 'text-red-400'
              }`}
            >
              ${entry.value?.toFixed(2)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (type === 'bar') {
    return (
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 11 }}
            tickLine={false}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="daily_pnl"
            fill="#6366f1"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#6b7280', fontSize: 11 }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#6b7280', fontSize: 11 }}
          tickLine={false}
          tickFormatter={(v) => `$${v}`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="cumulative_pnl"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#pnlGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}