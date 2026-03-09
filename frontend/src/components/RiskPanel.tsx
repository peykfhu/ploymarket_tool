// frontend/src/components/RiskPanel.tsx
import React, { useState } from 'react';
import { updateRiskSettings } from '../api';

export function RiskPanel() {
  const [settings, setSettings] = useState({
    max_position_size: 50,
    max_daily_loss: 200,
    min_edge: 0.08,
    max_concurrent: 20,
    stop_loss: 0.15,
  });
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    try {
      await updateRiskSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error('Failed to save settings', e);
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
        <h3 className="text-lg font-bold text-white mb-6">⚙️ 风控参数</h3>

        <div className="space-y-6">
          <SettingRow
            label="最大单笔仓位"
            description="单笔交易的最大金额"
            value={settings.max_position_size}
            suffix="USD"
            onChange={(v) => setSettings({ ...settings, max_position_size: v })}
          />

          <SettingRow
            label="每日最大亏损"
            description="达到后停止所有交易"
            value={settings.max_daily_loss}
            suffix="USD"
            onChange={(v) => setSettings({ ...settings, max_daily_loss: v })}
          />

          <SettingRow
            label="最小边际阈值"
            description="低于此值不开仓"
            value={settings.min_edge * 100}
            suffix="%"
            onChange={(v) => setSettings({ ...settings, min_edge: v / 100 })}
          />

          <SettingRow
            label="最大同时持仓"
            description="同时持有的最大仓位数"
            value={settings.max_concurrent}
            suffix="个"
            onChange={(v) => setSettings({ ...settings, max_concurrent: v })}
          />

          <SettingRow
            label="止损线"
            description="单笔亏损超过此比例自动平仓"
            value={settings.stop_loss * 100}
            suffix="%"
            onChange={(v) => setSettings({ ...settings, stop_loss: v / 100 })}
          />
        </div>

        <div className="mt-8 flex items-center gap-4">
          <button
            onClick={handleSave}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2.5 rounded-lg font-medium transition"
          >
            保存设置
          </button>

          {saved && (
            <span className="text-green-400 text-sm animate-count">
              ✅ 已保存
            </span>
          )}
        </div>
      </div>

      {/* 说明 */}
      <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800 mt-6">
        <h3 className="text-lg font-bold text-white mb-4">📋 API 配置说明</h3>
        <div className="space-y-3 text-sm text-gray-400">
          <p>需要在 <code className="bg-gray-800 px-2 py-0.5 rounded text-indigo-400">.env</code> 文件中配置以下 API：</p>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li><strong className="text-white">Polymarket API</strong> - 从 polymarket.com 获取 API Key</li>
            <li><strong className="text-white">NOAA API</strong> - 免费，从 weather.gov 申请</li>
            <li><strong className="text-white">Binance API</strong> - 从 binance.com 获取（只需读取权限）</li>
            <li><strong className="text-white">NewsAPI</strong> - 从 newsapi.org 获取（免费tier）</li>
            <li><strong className="text-white">Telegram Bot</strong>（可选）- @BotFather 创建</li>
          </ul>
          <p className="mt-4 text-yellow-400">
            ⚠️ 当前运行在 DRY_RUN 模式，不会真正下单。修改 .env 中 DRY_RUN=false 以启用真实交易。
          </p>
        </div>
      </div>
    </div>
  );
}

function SettingRow({
  label,
  description,
  value,
  suffix,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  suffix: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="text-white font-medium">{label}</div>
        <div className="text-xs text-gray-500 mt-0.5">{description}</div>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
          className="w-24 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-right text-sm focus:border-indigo-500 focus:outline-none"
        />
        <span className="text-gray-500 text-sm w-8">{suffix}</span>
      </div>
    </div>
  );
}