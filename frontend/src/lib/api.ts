const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

async function get<T>(path: string, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const login = (email: string, password: string) =>
  post<{ access_token: string; token_type: string }>("/auth/login", { email, password });

export const getCurrentUser = (token: string) =>
  get<{
    user: {
      id: number;
      email: string;
      role: string;
      organization_id: number;
      created_at: string;
    };
  }>("/auth/me", token);

export const healthCheck = () => get<{ status: string }>("/health");

export const getUnits = () => get<{ items: unknown[]; total: number }>("/units/");

export const getUnit = (token: string) =>
  get<{ unit: Record<string, unknown> }>(`/units/${encodeURIComponent(token)}`);

export const verifyProduct = (token: string) =>
  get<{
    unit: Record<string, unknown>;
    verification_event: { result: string; is_duplicate: boolean };
    warning?: string | null;
  }>(
    `/verify/${encodeURIComponent(token)}`,
  );

export const getUnitEvents = (productUnitId: number) =>
  get<{ items: unknown[]; total: number }>(`/events/${productUnitId}`);

export const getUnitReadings = (productUnitId: number) =>
  get<{ items: unknown[]; total: number }>(`/iot/${productUnitId}/readings`);

export const getLatestReading = (productUnitId: number) =>
  get<{ reading: Record<string, unknown> }>(`/iot/${productUnitId}/latest`);

export const getTelemetrySummary = () =>
  get<{
    items: Array<{
      unit: Record<string, unknown>;
      reading: Record<string, unknown> | null;
    }>;
    total: number;
    with_reading: number;
  }>("/iot/summary");