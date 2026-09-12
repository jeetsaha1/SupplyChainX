"use client";

import { useEffect, useState } from "react";

import { getLatestReading, getUnitEvents, verifyProduct } from "@/lib/api";

type Reading = {
  temperature: number;
  humidity: number;
  accel_magnitude: number;
  timestamp?: string;
};

type Unit = {
  id?: number;
  product_name?: string;
  serial_no?: string;
  batch_no?: string;
  status?: string;
  risk_level?: string;
  risk_score?: number;
};

type VerificationEvent = {
  result: string;
  is_duplicate: boolean;
};

export default function VerifyPage({
  params,
}: {
  params: { token: string };
}) {
  const [unit, setUnit] = useState<Unit | null>(null);
  const [reading, setReading] = useState<Reading | null>(null);
  const [events, setEvents] = useState<unknown[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [verification, setVerification] = useState<VerificationEvent | null>(null);

  useEffect(() => {
    verifyProduct(params.token)
      .then((data) => {
        const resolvedUnit = data.unit as Unit;
        setUnit(resolvedUnit);
        setWarning(data.warning ?? null);
        setVerification(data.verification_event as VerificationEvent);
        if (resolvedUnit.id) {
          return Promise.all([
            getLatestReading(resolvedUnit.id).then((latest) =>
              setReading(latest.reading as Reading),
            ),
            getUnitEvents(resolvedUnit.id).then((history) =>
              setEvents(history.items),
            ),
          ]);
        }
        return undefined;
      })
      .catch(() => setError("Product verification data is unavailable."));
  }, [params.token]);

  const riskLevel = unit?.risk_level ?? "Low";

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-100">
      <div className="mx-auto max-w-4xl">
        <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">SupplyChainX</p>
        <h1 className="mt-3 text-3xl font-semibold">Product verification</h1>
        {error && <p className="mt-6 text-rose-300">{error}</p>}
        {warning && <p className="mt-6 border border-amber-400/40 bg-amber-400/10 px-4 py-3 text-amber-100">{warning}</p>}
        {verification && (
          <p className={`mt-6 border px-4 py-3 ${verification.is_duplicate ? "border-amber-400/40 bg-amber-400/10 text-amber-100" : "border-emerald-400/40 bg-emerald-400/10 text-emerald-100"}`}>
            {verification.is_duplicate
              ? "Duplicate scan detected: this QR code was scanned recently from the same client."
              : "Scan verified: this is the first recent scan from this client."}
          </p>
        )}

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          <section className="border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-lg font-semibold">Digital Identity</h2>
            <p className="mt-4 text-slate-300">{unit?.product_name ?? "Loading product..."}</p>
            <p className="mt-2 text-sm text-slate-400">Serial: {unit?.serial_no ?? "-"}</p>
            <p className="text-sm text-slate-400">Batch: {unit?.batch_no ?? "-"}</p>
            <p className="mt-4 text-sm text-slate-400">Lifecycle events: {events.length}</p>
          </section>

          <section className="border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-lg font-semibold">Physical Evidence</h2>
            <p className="mt-4 text-sm text-slate-400">
              Temperature: {reading?.temperature ?? "-"} C
            </p>
            <p className="text-sm text-slate-400">Humidity: {reading?.humidity ?? "-"} %</p>
            <p className="text-sm text-slate-400">
              Shock magnitude: {reading?.accel_magnitude ?? "-"}
            </p>
          </section>
        </div>

        <div className="mt-8 inline-flex border border-cyan-400/50 px-4 py-2 text-sm text-cyan-200">
          Provenance Anomaly Detection: {riskLevel} ({unit?.risk_score ?? 0})
        </div>
      </div>
    </main>
  );
}