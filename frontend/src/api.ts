
const A='/api';

export const fetchDashboard=async()=>(await fetch(`${A}/dashboard`)).json();

export const fetchAgents=async()=>(await fetch(`${A}/agents`)).json();

export const startAgent=async(n:string)=>(await fetch(`${A}/agents/${n}/start`,{method:'POST'})).json();

export const stopAgent=async(n:string)=>(await fetch(`${A}/agents/${n}/stop`,{method:'POST'})).json();

export const fetchTrades=async(l=100)=>(await fetch(`${A}/trades?limit=${l}`)).json();

export const fetchActivities=async(l=50)=>(await fetch(`${A}/activities?limit=${l}`)).json();

export const fetchSettings=async()=>(await fetch(`${A}/settings`)).json();

export const saveSettings=async(s:any)=>(await fetch(`${A}/settings`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(s)})).json();

export const fetchScannedMarkets=async(cat?:string)=>(await fetch(`${A}/markets/scanned${cat?`?category=${cat}`:''}`)).json();

export const fetchTradeStats=async()=>(await fetch(`${A}/trades/stats`)).json();

export const fetchLogs=async(a?:string)=>(await fetch(`${A}/logs${a?`?agent_name=${a}`:''}`)).json();

export const fetchLivePositions=async()=>(await fetch(`${A}/positions/live`)).json();

export const closeTrade=async(id:number)=>(await fetch(`${A}/trades/${id}/close`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();

