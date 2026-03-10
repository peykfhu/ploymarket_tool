
import React,{useState} from 'react';

import {Trade} from '../types';

import {closeTrade} from '../api';



interface Props{

  trades:Trade[];

  showCloseButton?:boolean;

  livePnl?:Record<number,{unrealized_pnl:number;pnl_percent:number;current_price:number}>;

  onClose?:()=>void;

}



export function TradeLog({trades,showCloseButton=false,livePnl,onClose}:Props){

  const [closing,setClosing]=useState<number|null>(null);



  if(!trades.length)return(

    <div className="text-center py-8 text-gray-500"><div className="text-3xl mb-2">📭</div><p>暂无交易</p></div>

  );



  async function handleClose(id:number){

    if(!confirm('确认手动平仓？'))return;

    setClosing(id);

    try{

      const r=await closeTrade(id);

      alert(`平仓成功 PnL: $${r.pnl?.toFixed(4)||'?'}`);

      onClose?.();

    }catch(e){

      alert('平仓失败');

    }

    setClosing(null);

  }



  return(

    <div className="overflow-x-auto">

      <table className="w-full text-sm">

        <thead>

          <tr className="border-b border-gray-800 text-gray-500 text-xs">

            <th className="text-left py-2 px-2">时间</th>

            <th className="text-left py-2 px-2">Agent</th>

            <th className="text-left py-2 px-2">市场</th>

            <th className="text-left py-2 px-2">方向</th>

            <th className="text-right py-2 px-2">入场</th>

            <th className="text-right py-2 px-2">仓位</th>

            <th className="text-right py-2 px-2">边际</th>

            {livePnl&&<th className="text-right py-2 px-2">现价</th>}

            <th className="text-right py-2 px-2">盈亏</th>

            {showCloseButton&&<th className="text-center py-2 px-2">操作</th>}

          </tr>

        </thead>

        <tbody>

          {trades.map(t=>{

            const lp=livePnl?.[t.id];

            const unrealizedPnl=lp?.unrealized_pnl;

            const pnlPct=lp?.pnl_percent;

            const currentPrice=lp?.current_price;

            const profit=t.status==='open'?(unrealizedPnl||0)>=0:t.profit_loss>=0;



            return(

              <tr key={t.id} className="border-b border-gray-800/30 hover:bg-gray-800/20 transition-colors">

                <td className="py-2 px-2 text-gray-400 text-xs whitespace-nowrap">

                  {new Date(t.created_at).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}

                </td>

                <td className="py-2 px-2"><span className="text-xs bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">{t.agent_name.split(' ')[0]}</span></td>

                <td className="py-2 px-2 text-gray-300 max-w-[160px] truncate text-xs" title={t.market_title}>{t.market_title||t.market_id}</td>

                <td className="py-2 px-2"><span className={`text-xs ${t.direction.includes('YES')?'text-green-400':'text-red-400'}`}>{t.direction}</span></td>

                <td className="py-2 px-2 text-right text-gray-300 font-mono text-xs">${t.entry_price.toFixed(4)}</td>

                <td className="py-2 px-2 text-right text-gray-300 font-mono text-xs">${t.size.toFixed(2)}</td>

                <td className="py-2 px-2 text-right text-indigo-400 font-mono text-xs">{(t.edge*100).toFixed(1)}%</td>

                {livePnl&&(

                  <td className="py-2 px-2 text-right font-mono text-xs text-gray-400">

                    {currentPrice!==undefined?`$${currentPrice.toFixed(4)}`:'--'}

                  </td>

                )}

                <td className={`py-2 px-2 text-right font-mono font-bold text-xs ${

                  t.status==='open'

                    ?(unrealizedPnl!==undefined?(unrealizedPnl>=0?'text-green-400':'text-red-400'):'text-yellow-400')

                    :(profit?'text-green-400':'text-red-400')

                }`}>

                  {t.status==='open'

                    ?(unrealizedPnl!==undefined

                      ?<span>{unrealizedPnl>=0?'+':''}${unrealizedPnl.toFixed(4)} <span className="text-[10px]">({pnlPct?.toFixed(1)}%)</span></span>

                      :'持仓中')

                    :`${profit?'+':''}$${t.profit_loss.toFixed(2)}`

                  }

                </td>

                {showCloseButton&&(

                  <td className="py-2 px-2 text-center">

                    {t.status==='open'&&(

                      <button

                        onClick={()=>handleClose(t.id)}

                        disabled={closing===t.id}

                        className="px-2 py-1 rounded text-[10px] font-medium bg-red-900/30 text-red-400 hover:bg-red-900/50 transition-all active:scale-90 disabled:opacity-50"

                      >

                        {closing===t.id?'...':'✂️ 平仓'}

                      </button>

                    )}

                  </td>

                )}

              </tr>

            );

          })}

        </tbody>

      </table>

    </div>

  );

}

