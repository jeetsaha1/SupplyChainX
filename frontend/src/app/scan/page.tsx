"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Detector = {
  detect: (source: HTMLVideoElement) => Promise<Array<{ rawValue?: string }>>;
};

type DetectorConstructor = new (options?: { formats: string[] }) => Detector;

type BarcodeWindow = Window & {
  BarcodeDetector?: DetectorConstructor;
};

export default function ScanPage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState("Starting camera...");
  const [isSupported, setIsSupported] = useState(true);

  useEffect(() => {
    let active = true;
    const browserWindow = window as BarcodeWindow;
    const Detector = browserWindow.BarcodeDetector;

    if (!Detector || !navigator.mediaDevices?.getUserMedia) {
      setIsSupported(false);
      setStatus("QR camera scanning is not supported in this browser.");
      return () => undefined;
    }

    let detector: Detector;
    try {
      detector = new Detector({ formats: ["qr_code"] });
    } catch {
      setIsSupported(false);
      setStatus("QR camera scanning is not supported in this browser.");
      return () => undefined;
    }

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        if (!active || !videoRef.current) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStatus("Point the camera at a SupplyChainX QR code.");
        scan();
      } catch {
        setStatus("Camera permission was denied or no camera is available.");
      }
    }

    async function scan() {
      if (!active || !videoRef.current) return;
      try {
        const results = await detector.detect(videoRef.current);
        const value = results[0]?.rawValue;
        if (value) {
          const match = value.match(/\/verify\/([^/?#]+)/);
          if (match?.[1]) {
            setStatus("QR code detected. Opening verification...");
            router.push(`/verify/${encodeURIComponent(match[1])}`);
            return;
          }
          setStatus("This QR code is not a SupplyChainX verification code.");
        }
      } catch {
        // Camera frames can be unavailable while the video is initializing.
      }
      window.setTimeout(scan, 300);
    }

    start();
    return () => {
      active = false;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, [router]);

  return (
    <main className="min-h-screen bg-[#071018] px-6 py-12 text-slate-100">
      <div className="mx-auto max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-300">SupplyChainX</p>
        <h1 className="mt-4 text-3xl font-semibold">Scan product QR</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">Use the device camera to open a public product verification record.</p>
        <div className="mt-8 overflow-hidden border border-slate-800 bg-slate-900/70 p-4">
          {isSupported ? (
            <video className="aspect-video w-full bg-slate-950 object-cover" ref={videoRef} muted playsInline />
          ) : (
            <div className="flex aspect-video items-center justify-center bg-slate-950 px-6 text-center text-sm text-amber-200">{status}</div>
          )}
          <p className="mt-4 text-sm text-slate-300">{status}</p>
        </div>
        <a className="mt-5 inline-block text-sm text-cyan-300 hover:text-cyan-200" href="/">Back to control room</a>
      </div>
    </main>
  );
}
