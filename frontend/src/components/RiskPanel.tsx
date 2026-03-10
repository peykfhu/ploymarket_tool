
import React,{useState,useEffect} from 'react';

import {fetchSettings,saveSettings} from '../api';

export function RiskPanel(){

  const [s,setS]=useState<any>({max_position_size:50,max_daily_loss:200,min_edge:0.06,max_concurrent:20,stop_loss:0.15,daily_drawdown_limit:0.15,initial_balance:150,dry_run:true,interval_weather:600,interval_crypto:90,interval_politics:90,interval_sports:90,interval_endgame:30,interval_sports_endgame:30});

  const [saved,setSaved]=useState(false);

  const [saving,setSaving]=useState(false);

  const [loaded,setLoaded]=useState(false);

  useEffect(()=>{fetchSettings().then(d=>{setS((p:any)=>({...p,...d}));setLoaded(true);}).catch(()=>setLoaded(true));},[]);

  async function save(){setSaving(true);try{await saveSettings(s);setSaved(true);setTimeout(()=>setSaved(false),3000);}catch{}setSaving(false);}

  if(!loaded)return<div className="text-gray-500 p-8">加载中...</div>;

  return(

    <div className="max-w-2xl space-y-6">

      <Card title="🔄 交易模式"><div className="flex items-center justify-between"><div><div className="text-white font-medium">{s.dry_run?'🧪 模拟':'🔴 实盘'}</div><div className="text-xs text-gray-500 mt-0.5">{s.dry_run?'模拟资金':'⚠️ 真实资金！'}</div></div><button onClick={()=>setS({...s,dry_run:!s.dry_run})} className={`relative w-14 h-7 rounded-full transition-all active:scale-95 ${s.dry_run?'bg-gray-600':'bg-red-500'}`}><div className={`absolute top-0.5 w-6 h-6 rounded-full bg-white shadow transition-all ${s.dry_run?'left-0.5':'left-7'}`}/></button></div>{!s.dry_run&&<div className="mt-3 p-3 bg-red-900/20 border border-red-800/30 rounded-lg text-red-400 text-xs">⚠️ 实盘模式将获取你的Polymarket真实余额并使用真实资金下单</div>}</Card>

      <Card title="💰 资金"><Row label="模拟初始资金" desc="DRY_RUN的起始余额" value={s.initial_balance} suffix="USD" onChange={(v:number)=>setS({...s,initial_balance:v})}/></Card>

      <Card title="⏱️ 扫描间隔(秒)"><div className="text-xs text-yellow-400 mb-3">设置过低会被API限流，系统强制最小值</div>

        <Row label="天气Agent" desc="最小120s" value={s.interval_weather} suffix="s" onChange={(v:number)=>setS({...s,interval_weather:Math.max(v,120)})}/>

        <Row label="加密Agent" desc="最小30s" value={s.interval_crypto} suffix="s" onChange={(v:number)=>setS({...s,interval_crypto:Math.max(v,30)})}/>

        <Row label="政治Agent" desc="最小60s" value={s.interval_politics} suffix="s" onChange={(v:number)=>setS({...s,interval_politics:Math.max(v,60)})}/>

        <Row label="伤病Agent" desc="最小60s" value={s.interval_sports} suffix="s" onChange={(v:number)=>setS({...s,interval_sports:Math.max(v,60)})}/>

        <Row label="尾盘Agent" desc="最小15s" value={s.interval_endgame} suffix="s" onChange={(v:number)=>setS({...s,interval_endgame:Math.max(v,15)})}/>

        <Row label="体育尾盘" desc="最小15s(需要快)" value={s.interval_sports_endgame} suffix="s" onChange={(v:number)=>setS({...s,interval_sports_endgame:Math.max(v,15)})}/>

      </Card>

      <Card title="🛡️ 风控"><Row label="最大仓位" desc="" value={s.max_position_size} suffix="$" onChange={(v:number)=>setS({...s,max_position_size:v})}/><Row label="日最大亏损" desc="" value={s.max_daily_loss} suffix="$" onChange={(v:number)=>setS({...s,max_daily_loss:v})}/><Row label="日回撤限" desc="15%推荐" value={s.daily_drawdown_limit*100} suffix="%" onChange={(v:number)=>setS({...s,daily_drawdown_limit:v/100})}/><Row label="最小边际" desc="" value={s.min_edge*100} suffix="%" onChange={(v:number)=>setS({...s,min_edge:v/100})}/><Row label="最大持仓" desc="" value={s.max_concurrent} suffix="个" onChange={(v:number)=>setS({...s,max_concurrent:v})}/><Row label="止损" desc="" value={s.stop_loss*100} suffix="%" onChange={(v:number)=>setS({...s,stop_loss:v/100})}/></Card>

      <div className="flex items-center gap-4"><button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2.5 rounded-lg font-medium transition-all active:scale-95 disabled:opacity-50">{saving?'...':'💾 保存'}</button>{saved&&<span className="text-green-400 text-sm">✅ 已持久化</span>}</div>

      <Card title="📋 API配置"><div className="bg-gray-800/50 rounded-lg p-4 font-mono text-xs space-y-1"><p className="text-gray-400"># Polymarket</p><p><span className="text-green-400">POLYMARKET_API_KEY</span>=apiKey</p><p><span className="text-green-400">POLYMARKET_API_SECRET</span>=secret</p><p><span className="text-green-400">POLYMARKET_PASSPHRASE</span>=passphrase</p><p className="mt-2 text-gray-400"># 钱包(Polygon链)</p><p><span className="text-blue-400">POLYMARKET_WALLET_ADDRESS</span>=0x...</p><p><span className="text-blue-400">POLYMARKET_PRIVATE_KEY</span>=私钥</p></div></Card>

    </div>

  );

}

function Card({title,children}:{title:string;children:React.ReactNode}){return<div className="bg-gray-900 rounded-2xl p-6 border border-gray-800"><h3 className="text-base font-bold text-white mb-4">{title}</h3><div className="space-y-4">{children}</div></div>;}

function Row({label,desc,value,suffix,onChange}:{label:string;desc:string;value:number;suffix:string;onChange:(v:number)=>void;}){return<div className="flex items-center justify-between"><div><div className="text-white text-sm">{label}</div>{desc&&<div className="text-[10px] text-gray-500">{desc}</div>}</div><div className="flex items-center gap-1.5"><input type="number" value={value} onChange={e=>onChange(parseFloat(e.target.value)||0)} className="w-20 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-white text-right text-sm focus:border-indigo-500 focus:outline-none"/><span className="text-gray-500 text-[10px] w-6">{suffix}</span></div></div>;}

