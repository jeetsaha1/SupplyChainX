"use client";

import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";

import {
  getLatestReading,
  getUnit,
  getUnitEvents,
  getUnits,
  healthCheck,
} from "@/lib/api";

type Connection = "checking" | "connected" | "disconnected";

type AuthUser = {
  email: string;
  role: string;
};

type Unit = {
  id: number;
  qr_public_token: string;
  product_name: string;
  serial_no: string;
  batch_no: string;
  expiry_date: string;
  status: string;
  risk_score: number;
  risk_level: string;
  scan_count: number;
};

type Reading = {
  temperature: number;
  humidity: number;
  accel_magnitude: number;
  timestamp: string;
};

type Event = {
  event_type: string;
  location_label?: string;
  timestamp: string;
  chain_status: string;
  tx_hash?: string;
};

type UnitSummary = Pick<
  Unit,
  "id" | "qr_public_token" | "product_name" | "serial_no"
>;

const statusTone: Record<string, string> = {
  low: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  medium: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  high: "border-rose-400/30 bg-rose-400/10 text-rose-200",
};

export default function Home() {
  const [connection, setConnection] = useState<Connection>("checking");
  const [unit, setUnit] = useState<Unit | null>(null);
  const [units, setUnits] = useState<UnitSummary[]>([]);
  const [selectedToken, setSelectedToken] = useState("");
  const [reading, setReading] = useState<Reading | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;

    const storedUser = window.localStorage.getItem("scx_user");
    if (storedUser) {
      try {
        setAuthUser(JSON.parse(storedUser) as AuthUser);
      } catch {
        window.localStorage.removeItem("scx_user");
      }
    }

    async function loadDashboard(token?: string) {
      try {
        setIsRefreshing(true);
        const [health, unitsResponse] = await Promise.all([
          healthCheck(),
          getUnits(),
        ]);
        if (!active) return;

        setConnection(health.status === "ok" ? "connected" : "disconnected");

        const availableUnits = unitsResponse.items as UnitSummary[];
        setUnits(availableUnits);
        const activeToken = token || selectedToken || availableUnits[0]?.qr_public_token;
        const firstUnit = availableUnits.find((item) => item.qr_public_token === activeToken);
        if (!firstUnit) {
          setError("No seeded product units are available yet.");
          return;
        }

        const unitResponse = await getUnit(firstUnit.qr_public_token);
        const resolvedUnit = unitResponse.unit as Unit;
        if (!active) return;
        setSelectedToken(firstUnit.qr_public_token);
        setUnit(resolvedUnit);

        const [eventResponse, latestResponse] = await Promise.all([
          getUnitEvents(resolvedUnit.id),
          getLatestReading(resolvedUnit.id).catch(() => null),
        ]);
        if (!active) return;
        setEvents(eventResponse.items as Event[]);
        if (latestResponse?.reading) {
          setReading(latestResponse.reading as Reading);
        }
        setError(null);
      } catch {
        if (!active) return;
        setConnection("disconnected");
        setError("The integration services are not available.");
      } finally {
        if (active) setIsRefreshing(false);
      }
    }

    loadDashboard();
    const refreshTimer = window.setInterval(() => loadDashboard(), 10000);
    return () => {
      active = false;
      window.clearInterval(refreshTimer);
    };
  }, [selectedToken]);

  function selectProduct(token: string) {
    setSelectedToken(token);
  }

  const riskLevel = unit?.risk_level || "low";
  const tone = statusTone[riskLevel] ?? statusTone.low;
  const browserOrigin = typeof window === "undefined" ? "" : window.location.origin;
  const verificationUrl = unit
    ? `${browserOrigin}/verify/${unit.qr_public_token}`
    : "";

  return (
    <main className="min-h-screen bg-[#071018] text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
        <header className="relative flex flex-col gap-5 border-b border-slate-800 pb-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">
              SupplyChainX / Control Room
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
              One product. Every proof point.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Digital identity, blockchain lifecycle evidence, and live physical telemetry in one verification view.
            </p>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-300">
            <span className={`h-2.5 w-2.5 rounded-full ${connection === "connected" ? "bg-emerald-400" : "bg-amber-400"}`} />
            {connection === "checking" && "Connecting to integration layer"}
            {connection === "connected" && "Backend Connected: OK"}
            {connection === "disconnected" && "Backend Disconnected"}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400 md:absolute md:right-10 md:top-8">
            {authUser ? (
              <>
                <span className="border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-emerald-200">
                  {authUser.role} · {authUser.email}
                </span>
                <button
                  className="border border-slate-700 px-3 py-2 text-slate-300 hover:border-cyan-300 hover:text-cyan-200"
                  type="button"
                  onClick={() => {
                    window.localStorage.removeItem("scx_access_token");
                    window.localStorage.removeItem("scx_user");
                    setAuthUser(null);
                  }}
                >
                  Sign out
                </button>
              </>
            ) : (
              <a className="border border-slate-700 px-3 py-2 text-slate-300 hover:border-cyan-300 hover:text-cyan-200" href="/login">
                Operator sign in
              </a>
            )}
          </div>
        </header>

        <div className="mt-6 flex flex-col gap-3 border border-slate-800 bg-slate-900/60 p-4 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex min-w-0 items-center gap-3 text-sm text-slate-400">
            <span className="shrink-0 uppercase tracking-[0.15em]">Product</span>
            <select
              className="min-w-0 flex-1 border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300 sm:min-w-[22rem]"
              value={selectedToken}
              onChange={(event) => selectProduct(event.target.value)}
              disabled={units.length === 0}
            >
              {units.length === 0 && <option value="">Loading catalog...</option>}
              {units.map((item) => (
                <option key={item.qr_public_token} value={item.qr_public_token}>
                  {item.product_name} · {item.serial_no}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="border border-cyan-300/50 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-300/10 disabled:cursor-wait disabled:opacity-50"
            onClick={() => loadDashboardForSelectedProduct()}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Refreshing..." : "Refresh evidence"}
          </button>
        </div>

        {error && (
          <div className="mt-6 border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            {error}
          </div>
        )}

        <section className="mt-8 grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Digital Identity</p>
                <h2 className="mt-2 text-2xl font-semibold">{unit?.product_name ?? "Loading product..."}</h2>
                <p className="mt-2 text-sm text-slate-400">Serial {unit?.serial_no ?? "-"} · Batch {unit?.batch_no ?? "-"}</p>
              </div>
              <div className={`border px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] ${tone}`}>
                {riskLevel} risk
              </div>
            </div>
            <div className="mt-8 grid gap-4 border-t border-slate-800 pt-5 sm:grid-cols-3">
              <Metric label="Product status" value={unit?.status ?? "-"} />
              <Metric label="Risk score" value={unit ? `${unit.risk_score}/100` : "-"} />
              <Metric label="Verification scans" value={unit?.scan_count?.toString() ?? "-"} />
            </div>
          </div>

          <div className="border border-cyan-400/20 bg-cyan-400/[0.04] p-6 lg:col-span-2">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
              <div className="flex h-44 w-44 shrink-0 items-center justify-center bg-white p-3">
                {verificationUrl ? (
                  <QRCodeSVG value={verificationUrl} size={160} level="M" includeMargin />
                ) : (
                  <span className="text-center text-xs text-slate-500">Preparing QR</span>
                )}
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Judge demo / public proof</p>
                <h2 className="mt-2 text-2xl font-semibold">Scan to verify this medicine</h2>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-400">
                  The QR contains only the opaque public token. Scanning it opens the public verification view with identity, lifecycle, IoT evidence, and risk state.
                </p>
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
                  <code className="max-w-full overflow-hidden text-ellipsis whitespace-nowrap border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300">
                    {verificationUrl || "Loading verification URL..."}
                  </code>
                  {verificationUrl && (
                    <a
                      className="shrink-0 border border-cyan-300/50 px-4 py-2 text-center text-sm font-medium text-cyan-200 transition hover:bg-cyan-300/10"
                      href={verificationUrl}
                    >
                      Open verification
                    </a>
                  )}
                </div>
                <a className="mt-4 inline-block text-sm text-cyan-300 hover:text-cyan-200" href="/scan">
                  Use camera to scan a product QR
                </a>
              </div>
            </div>
          </div>

          <div className="border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Physical Evidence</p>
            <h2 className="mt-2 text-2xl font-semibold">IoT telemetry</h2>
            <div className="mt-6 grid grid-cols-3 gap-3">
              <Metric label="Temperature" value={reading ? `${reading.temperature.toFixed(1)} C` : "-"} />
              <Metric label="Humidity" value={reading ? `${reading.humidity.toFixed(1)} %` : "-"} />
              <Metric label="Shock" value={reading ? reading.accel_magnitude.toFixed(2) : "-"} />
            </div>
            <p className="mt-6 text-xs text-slate-500">
              {reading ? `Last reading ${new Date(reading.timestamp).toLocaleString()}` : "Waiting for gateway telemetry"}
            </p>
          </div>
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Blockchain evidence</p>
                <h2 className="mt-2 text-xl font-semibold">Lifecycle timeline</h2>
              </div>
              <span className="text-sm text-slate-500">{events.length} events</span>
            </div>
            <div className="mt-6 space-y-5">
              {events.length === 0 && <p className="text-sm text-slate-500">No lifecycle events loaded.</p>}
              {events.map((event, index) => (
                <div className="relative border-l border-cyan-400/40 pl-5" key={`${event.timestamp}-${index}`}>
                  <span className="absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-cyan-300" />
                  <p className="text-sm font-semibold capitalize">{event.event_type}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {event.location_label ?? "Location unavailable"} · {new Date(event.timestamp).toLocaleDateString()}
                  </p>
                  <p className="mt-1 text-xs text-emerald-300">Chain: {event.chain_status}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-slate-800 bg-slate-900/70 p-6">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Integration status</p>
            <h2 className="mt-2 text-xl font-semibold">Evidence pipeline</h2>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <PipelineStep title="Arduino UNO" detail="DHT11 + MPU9250 / COM3" active={Boolean(reading)} />
              <PipelineStep title="FastAPI + ORM" detail="IoT devices + readings" active={connection === "connected"} />
              <PipelineStep title="Provenance Anomaly Detection" detail="Risk badge and flags" active={Boolean(unit)} />
            </div>
            <p className="mt-7 border-t border-slate-800 pt-5 text-sm leading-6 text-slate-400">
              Raw sensor data stays off-chain. Lifecycle hashes provide tamper evidence while physical telemetry supplies the real-world context.
            </p>
          </div>
        </section>

      </div>
    </main>
  );

  async function loadDashboardForSelectedProduct() {
    if (!selectedToken) return;
    setIsRefreshing(true);
    try {
      const unitResponse = await getUnit(selectedToken);
      const resolvedUnit = unitResponse.unit as Unit;
      const [eventResponse, latestResponse] = await Promise.all([
        getUnitEvents(resolvedUnit.id),
        getLatestReading(resolvedUnit.id).catch(() => null),
      ]);
      setUnit(resolvedUnit);
      setEvents(eventResponse.items as Event[]);
      if (latestResponse?.reading) {
        setReading(latestResponse.reading as Reading);
      }
      setError(null);
    } catch {
      setError("The selected product evidence is unavailable.");
    } finally {
      setIsRefreshing(false);
    }
  }
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.15em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-medium text-slate-100">{value}</p>
    </div>
  );
}

function PipelineStep({ title, detail, active }: { title: string; detail: string; active: boolean }) {
  return (
    <div className="border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${active ? "bg-emerald-400" : "bg-slate-600"}`} />
        <p className="text-sm font-semibold">{title}</p>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  );
}
