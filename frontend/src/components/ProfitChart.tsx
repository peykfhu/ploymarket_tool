
import React from 'react';

import {ResponsiveContainer,AreaChart,Area,BarChart,Bar,LineChart,Line,XAxis,YAxis,Tooltip,CartesianGrid} from 'recharts';

interface Props{data:any[];type?:'area'|'bar'|'line';}

export function ProfitChart({data,type='area'}:Props){

  if(!data?.length)return<div className="flex items-center justify-center h-[200px] text-gray-500 text-sm">📊 暂无数据</div>;

  const Tip=({active,payload,label}:any)=>{

    if(!active||!payload?.length)return null;

    return<div className="bg-gray-800 border border-gray-700 rounded px-2 py-1"><p className="text-gray-400 text-[10px]">{label}</p><p className={`text-xs font-bold ${payload[0].value>=0?'text-green-400':'text-red-400'}`}>${payload[0].value?.toFixed(2)}</p></div>;

  };

  if(type==='bar')return(

    <ResponsiveContainer width="100%" height={200}><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#374151"/><XAxis dataKey="date" tick={{fill:'#6b7280',fontSize:10}} tickLine={false}/><YAxis tick={{fill:'#6b7280',fontSize:10}} tickLine={false} tickFormatter={v=>`$${v}`}/><Tooltip content={<Tip/>}/><Bar dataKey="daily_pnl" fill="#6366f1" radius={[3,3,0,0]}/></BarChart></ResponsiveContainer>

  );

  if(type==='line')return(

    <ResponsiveContainer width="100%" height={200}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#374151"/><XAxis dataKey="date" tick={{fill:'#6b7280',fontSize:10}} tickLine={false}/><YAxis tick={{fill:'#6b7280',fontSize:10}} tickLine={false} tickFormatter={v=>`$${v}`}/><Tooltip content={<Tip/>}/><Line type="monotone" dataKey="balance" stroke="#22c55e" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer>

  );

  return(

    <ResponsiveContainer width="100%" height={200}><AreaChart data={data}><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/><stop offset="95%" stopColor="#6366f1" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#374151"/><XAxis dataKey="date" tick={{fill:'#6b7280',fontSize:10}} tickLine={false}/><YAxis tick={{fill:'#6b7280',fontSize:10}} tickLine={false} tickFormatter={v=>`$${v}`}/><Tooltip content={<Tip/>}/><Area type="monotone" dataKey="cumulative_pnl" stroke="#6366f1" strokeWidth={2} fill="url(#g)"/></AreaChart></ResponsiveContainer>

  );

}

