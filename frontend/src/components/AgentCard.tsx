
import React, { useState } from 'react';

import { AgentState } from '../types';

import { startAgent, stopAgent } from '../api';

const icons: Record<string,string> = {weather:'🌦️',crypto:'₿',politics:'🏛️',sports:'🏥',endgame:'🎯',sports_endgame:'🏆'};

const grads: Record<string,string> = {weather:'from-blue-600 to-cyan-600',crypto:'from-orange-500 to-yellow-500',politics:'from-purple-600 to-pink-500',sports:'from-green-500 to-emerald-500',endgame:'from-red-500 to-orange-500',sports_endgame:'from-yellow-500 to-red-500'};

export function AgentCard({agentKey,agent}:{agentKey:string;agent:AgentState}) {

  const [busy,setBusy]=useState(false);

  const [opt,setOpt]=useState<string|null>(null);

  const st=opt||agent.status;

  const on=st==='running';

  async function toggle(){setBusy(true);setOpt(on?'stopped':'running');try{if(on)await stopAgent(agentKey);else await startAgent(agentKey);}catch{setOpt(null);}setTimeout(()=>{setBusy(false);setOpt(null);},1500);}

  return(

    <div className={`bg-gray-900 rounded-2xl p-4 border transition-all hover:translate-y-[-1px] ${on?'border-indigo-500/30 shadow-lg shadow-indigo-500/5':'border-gray-800'}`}>

      <div className="flex items-center justify-between mb-3">

        <div className="flex items-center gap-2">

          <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${grads[agentKey]||'from-gray-600 to-gray-700'} flex items-center justify-center text-base shadow`}>{icons[agentKey]||'🤖'}</div>

          <div><h3 className="font-semibold text-white text-xs">{agent.name}</h3>

          <div className="flex items-center gap-1 mt-0.5"><div className={`w-1.5 h-1.5 rounded-full ${on?'bg-green-400 animate-pulse':'bg-gray-500'}`}/><span className={`text-[10px] ${on?'text-green-400':'text-gray-500'}`}>{on?`${agent.interval}s`:'停止'}</span></div></div>

        </div>

        <button onClick={toggle} disabled={busy} className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all active:scale-90 disabled:opacity-50 ${on?'bg-red-900/30 text-red-400':'bg-green-900/30 text-green-400'}`}>{busy?'...':on?'停':'启'}</button>

      </div>

      <div className="grid grid-cols-3 gap-2 text-center">

        <div><div className="text-[9px] text-gray-500">交易</div><div className="text-sm font-bold text-white">{agent.total_trades}</div></div>

        <div><div className="text-[9px] text-gray-500">胜率</div><div className={`text-sm font-bold ${agent.win_rate>=60?'text-green-400':'text-yellow-400'}`}>{agent.win_rate.toFixed(0)}%</div></div>

        <div><div className="text-[9px] text-gray-500">盈亏</div><div className={`text-sm font-bold ${(agent.total_pnl||0)>=0?'text-green-400':'text-red-400'}`}>${(agent.total_pnl||0).toFixed(0)}</div></div>

      </div>

      {agent.last_signal&&<div className="mt-2 p-1.5 bg-gray-800/60 rounded text-[10px] text-gray-400 truncate">{agent.last_signal}</div>}

      <div className="mt-1.5 flex justify-between text-[9px] text-gray-600"><span>扫:{agent.scan_count}</span><span>机会:{agent.opportunities_found}</span>{agent.errors>0&&<span className="text-red-400">❌{agent.errors}</span>}</div>

    </div>

  );

}

