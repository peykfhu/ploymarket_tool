
import React,{useState,useEffect,useCallback} from 'react';

import {DashboardData} from '../types';

import {AgentCard} from './AgentCard';

import {TradeLog} from './TradeLog';

import {ProfitChart} from './ProfitChart';

import {LiveTicker} from './LiveTicker';

import {RiskPanel} from './RiskPanel';

import {Header} from './Header';

import {fetchScannedMarkets,fetchLivePositions} from '../api';



interface Props{data:DashboardData;isConnected:boolean;onRefresh:()=>void;}



export function Dashboard({data,isConnected,onRefresh}:Props){

  const [tab,setTab]=useState<'overview'|'trades'|'markets'|'settings'>('overview');

  const [markets,setMarkets]=useState<Record<string,any[]>>({});

  const [mCat,setMCat]=useState('climate');

  const [mLoading,setMLoading]=useState(false);

  const [livePnl,setLivePnl]=useState<Record<number,any>>({});

  const {overview:o,agents,recent_trades,open_positions,cumulative_pnl,daily_pnl,activities,strategy_stats}=data;



  // 实时刷新持仓盈亏

  const refreshPositions=useCallback(async()=>{

    try{

      const live=await fetchLivePositions();

      const map:Record<number,any>={};

      for(const p of live){

        map[p.id]={unrealized_pnl:p.unrealized_pnl,pnl_percent:p.pnl_percent,current_price:p.current_price};

      }

      setLivePnl(map);

    }catch{}

  },[]);



  useEffect(()=>{

    if(open_positions.length>0){

      refreshPositions();

      const i=setInterval(refreshPositions,5000); // 每5秒刷新

      return()=>clearInterval(i);

    }

  },[open_positions.length,refreshPositions]);



  async function loadMarkets(cat:string){

    setMCat(cat);

    setMLoading(true);

    try{

      const r=await fetchScannedMarkets(cat);

      setMarkets(prev=>({...prev,[cat]:r?.markets||r?.[cat]||[]}));

    }catch{}

    setMLoading(false);

  }



  useEffect(()=>{if(tab==='markets')loadMarkets(mCat);},[tab]);



  const balanceCurve=cumulative_pnl.map(p=>({date:p.date,balance:o.initial_balance+(p.cumulative_pnl||0)}));



  return(

    <div className="min-h-screen bg-gray-950">

      <Header isConnected={isConnected} isDryRun={data.dry_run} onRefresh={onRefresh}/>

      <div className="max-w-7xl mx-auto px-4 py-5">

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">

          <Stat icon="💰" label="余额" value={`$${o.current_balance.toFixed(2)}`} sub={o.total_pnl}/>

          <Stat icon="📈" label="总盈亏" value={`$${o.total_pnl.toFixed(2)}`} positive={o.total_pnl>=0}/>

          <Stat icon="📅" label="今日" value={`$${(o.today_pnl||0).toFixed(2)}`} positive={(o.today_pnl||0)>=0}/>

          <Stat icon="🎯" label="ROI" value={`${o.roi.toFixed(1)}%`} positive={o.roi>=0}/>

          <Stat icon="🔄" label="交易" value={String(o.total_trades)}/>

          <Stat icon="✅" label="胜率" value={`${o.win_rate.toFixed(1)}%`} positive={o.win_rate>=50}/>

          <Stat icon="📊" label="持仓" value={String(o.open_positions)}/>

        </div>



        {strategy_stats&&Object.keys(strategy_stats).length>0&&(

          <div className="flex gap-3 mb-5 overflow-x-auto pb-1">

            {Object.entries(strategy_stats).map(([k,v])=>(

              <div key={k} className="bg-gray-900 rounded-xl px-4 py-2 border border-gray-800 shrink-0">

                <div className="text-[10px] text-gray-500">{k==='info_arb'?'⚡信息差':k==='endgame'?'🎯尾盘':k}</div>

                <div className="flex gap-3 mt-1"><span className="text-xs text-white font-bold">{v.trades}笔</span><span className={`text-xs ${v.win_rate>=60?'text-green-400':'text-yellow-400'}`}>{v.win_rate.toFixed(0)}%</span><span className={`text-xs font-bold ${v.pnl>=0?'text-green-400':'text-red-400'}`}>${v.pnl.toFixed(2)}</span></div>

              </div>

            ))}

          </div>

        )}



        <div className="flex gap-2 mb-5">

          {(['overview','trades','markets','settings'] as const).map(t=>(

            <button key={t} onClick={()=>setTab(t)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all active:scale-95 ${tab===t?'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20':'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>

              {t==='overview'?'📊总览':t==='trades'?'📋交易':t==='markets'?'🔍市场':'⚙️设置'}

            </button>

          ))}

        </div>



        {tab==='overview'&&(

          <>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-5">

              {Object.entries(agents).map(([k,a])=><AgentCard key={k} agentKey={k} agent={a}/>)}

            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">

              <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800"><h3 className="text-sm font-bold text-white mb-3">💰 资金曲线</h3><ProfitChart data={balanceCurve} type="line"/></div>

              <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800"><h3 className="text-sm font-bold text-white mb-3">📈 累计盈亏</h3><ProfitChart data={cumulative_pnl}/></div>

              <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800"><h3 className="text-sm font-bold text-white mb-3">📊 每日盈亏</h3><ProfitChart data={daily_pnl} type="bar"/></div>

            </div>

            {open_positions.length>0&&(

              <div className="bg-gray-900 rounded-2xl p-5 border border-yellow-800/30 mb-5">

                <div className="flex items-center justify-between mb-3">

                  <h3 className="text-sm font-bold text-yellow-400">⚡ 当前持仓 ({open_positions.length})</h3>

                  <button onClick={refreshPositions} className="text-xs text-gray-500 hover:text-white transition-all active:scale-90">🔄 刷新盈亏</button>

                </div>

                <TradeLog trades={open_positions} showCloseButton={true} livePnl={livePnl} onClose={()=>{onRefresh();refreshPositions();}}/>

              </div>

            )}

            <LiveTicker activities={activities||[]}/>

            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800 mt-5"><h3 className="text-sm font-bold text-white mb-3">🔄 最近交易</h3><TradeLog trades={recent_trades.slice(0,15)}/></div>

          </>

        )}



        {tab==='trades'&&(

          <div className="space-y-5">

            {open_positions.length>0&&(

              <div className="bg-gray-900 rounded-2xl p-5 border border-yellow-800/30">

                <div className="flex items-center justify-between mb-3">

                  <h3 className="text-sm font-bold text-yellow-400">⚡ 持仓 ({open_positions.length})</h3>

                  <button onClick={refreshPositions} className="text-xs text-gray-500 hover:text-white active:scale-90">🔄 刷新</button>

                </div>

                <TradeLog trades={open_positions} showCloseButton={true} livePnl={livePnl} onClose={()=>{onRefresh();refreshPositions();}}/>

              </div>

            )}

            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800"><h3 className="text-sm font-bold text-white mb-3">📋 全部交易</h3><TradeLog trades={recent_trades}/></div>

          </div>

        )}



        {tab==='markets'&&(

          <div className="space-y-5">

            <div className="flex gap-2">

              {[{key:'climate',label:'🌦️气候科学'},{key:'sports',label:'🏆体育'},{key:'crypto',label:'₿加密'}].map(c=>(

                <button key={c.key} onClick={()=>loadMarkets(c.key)} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all active:scale-95 ${mCat===c.key?'bg-indigo-600 text-white':'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>{c.label}</button>

              ))}

            </div>

            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">

              <div className="flex items-center justify-between mb-4"><h3 className="text-sm font-bold text-white">{mCat==='climate'?'🌦️气候':mCat==='sports'?'🏆体育':'₿加密'} 市场</h3><span className="text-xs text-gray-500">{(markets[mCat]||[]).length}个</span></div>

              {mLoading&&<div className="text-center py-8"><div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"/></div>}

              {!mLoading&&!(markets[mCat]||[]).length&&<div className="text-center py-8 text-gray-500"><p className="text-sm">暂无活跃市场</p></div>}

              <div className="space-y-2">

                {!mLoading&&(markets[mCat]||[]).map((m:any,i:number)=>(

                  <div key={m.id||i} className="flex items-center justify-between p-3 bg-gray-800/40 rounded-lg hover:bg-gray-800/60 transition-colors">

                    <div className="flex-1 min-w-0 mr-3"><p className="text-sm text-white truncate">{m.question}</p>

                      <div className="flex gap-3 mt-1">{m.end_date&&<span className="text-[10px] text-gray-500">截止:{new Date(m.end_date).toLocaleDateString('zh-CN')}</span>}{m.volume>0&&<span className="text-[10px] text-gray-500">Vol:${Number(m.volume).toLocaleString()}</span>}</div>

                    </div>

                    <div className="text-right shrink-0">{m.yes_price!=null?<div className={`text-lg font-bold font-mono ${m.yes_price>0.5?'text-green-400':m.yes_price>0.2?'text-yellow-400':'text-red-400'}`}>{(m.yes_price*100).toFixed(1)}¢</div>:<div className="text-gray-500">--</div>}<div className="text-[10px] text-gray-500">YES</div></div>

                  </div>

                ))}

              </div>

            </div>

          </div>

        )}



        {tab==='settings'&&<RiskPanel/>}

      </div>

    </div>

  );

}



function Stat({icon,label,value,sub,positive}:{icon:string;label:string;value:string;sub?:number;positive?:boolean;}){

  const c=positive===undefined?'text-white':positive?'text-green-400':'text-red-400';

  return<div className="bg-gray-900 rounded-xl p-3 border border-gray-800 hover:border-gray-700 transition-all"><div className="flex items-center gap-1 mb-0.5"><span className="text-sm">{icon}</span><span className="text-[9px] text-gray-500 uppercase">{label}</span></div><div className={`text-lg font-bold ${c}`}>{value}</div>{sub!==undefined&&<div className={`text-[10px] ${sub>=0?'text-green-500':'text-red-500'}`}>{sub>=0?'+':''}{sub.toFixed(2)}</div>}</div>;

}

