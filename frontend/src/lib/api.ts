const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function api<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json() as Promise<T>;
}

export const fetcher = (path: string) => api(path);

export type CountryPairFlow = { from: string; to: string; net_kwh: number; from_date: string; to_date: string };
export type StorageRow = { date: string; country: string; full_pct: number | null; working_gas_twh: number | null; injection_gwh: number | null; withdrawal_gwh: number | null };
export type LngRow = { date: string; terminal_id: string; sendout_gwh: number | null; inventory_gwh: number | null; dtmi_gwh: number | null };
export type ForecastPoint = { target_date: string; country: string; gwh: number; p10: number; p90: number; model_version: string };
