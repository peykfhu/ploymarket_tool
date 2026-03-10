
import React from 'react';

import { Activity } from '../types';



export function LiveTicker({ activities }: { activities: Activity[] }) {

  if (!activities?.length) return null;



  return (

    <div className="bg-gray-900 rounded-2xl p-4 border border-gray-800">

      <div className="flex items-center gap-2 mb-3">

        <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />

        <span className="text-sm font-medium text-gray-400">实时操作流</span>

      </div>

      <div className="space-y-1.5 max-h-[300px] overflow-y-auto">

        {activities.map((a, i) => (

          <div key={a.id || i} className={`flex items-start gap-2 p-2 rounded-lg transition-all ${i === 0 ? 'bg-indigo-900/15 border border-indigo-800/20' : 'bg-gray-800/30'}`}>

            <span className="text-sm mt-0.5 shrink-0">{a.icon}</span>

            <div className="min-w-0 flex-1">

              <div className="flex items-center gap-2">

                <span className="text-[10px] bg-gray-700/50 px-1.5 py-0.5 rounded text-gray-400">{a.agent_name}</span>

                <span className="text-xs text-white font-medium">{a.action}</span>

              </div>

              {a.detail && <p className="text-[11px] text-gray-400 mt-0.5 truncate">{a.detail}</p>}

            </div>

            <span className="text-[10px] text-gray-600 shrink-0 mt-0.5">

              {new Date(a.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}

            </span>

          </div>

        ))}

      </div>

    </div>

  );

}

