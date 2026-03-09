// frontend/src/api.ts
const API_BASE = '/api';

export async function fetchDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch dashboard');
  return res.json();
}

export async function fetchAgents() {
  const res = await fetch(`${API_BASE}/agents`);
  if (!res.ok) throw new Error('Failed to fetch agents');
  return res.json();
}

export async function startAgent(name: string) {
  const res = await fetch(`${API_BASE}/agents/${name}/start`, { method: 'POST' });
  return res.json();
}

export async function stopAgent(name: string) {
  const res = await fetch(`${API_BASE}/agents/${name}/stop`, { method: 'POST' });
  return res.json();
}

export async function fetchTrades(limit = 100) {
  const res = await fetch(`${API_BASE}/trades?limit=${limit}`);
  return res.json();
}

export async function fetchTradeStats() {
  const res = await fetch(`${API_BASE}/trades/stats`);
  return res.json();
}

export async function fetchLogs(agentName?: string) {
  const url = agentName
    ? `${API_BASE}/logs?agent_name=${agentName}`
    : `${API_BASE}/logs`;
  const res = await fetch(url);
  return res.json();
}

export async function updateRiskSettings(settings: Record<string, any>) {
  const res = await fetch(`${API_BASE}/settings/risk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  return res.json();
}