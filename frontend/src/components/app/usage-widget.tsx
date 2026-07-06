import { useEffect, useState } from "react";
import { getEmbedToken } from "@/lib/api";

// VoiceGateway's hosted widget iframe; teal accent to match its brand.
const WIDGET_URL =
  import.meta.env.VITE_VG_WIDGET_URL ??
  "https://dash.voicegateway.dev/embed/usage";
const ACCENT = "1f96aa";
const HEIGHT = 236;

/**
 * The signed-in realtor's own call usage, rendered by VoiceGateway's hosted
 * widget. Fetches a short-lived token scoped to this realtor from our backend
 * (the vk_ key stays server-side) and embeds the iframe. If the widget is not
 * configured, it renders nothing rather than a broken frame.
 */
export function UsageWidget() {
  const [token, setToken] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    getEmbedToken()
      .then((d) => {
        if (alive) setToken(d.token);
      })
      .catch(() => {
        if (alive) setFailed(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (failed) return null;
  if (!token) {
    return (
      <div
        className="animate-pulse rounded-xl border bg-muted/40"
        style={{ height: HEIGHT }}
        aria-hidden
      />
    );
  }

  const src = `${WIDGET_URL}?token=${encodeURIComponent(
    token,
  )}&accent=${ACCENT}&period=month`;
  return (
    <iframe
      src={src}
      title="Your VoiceGateway usage"
      className="w-full rounded-xl border-0"
      height={HEIGHT}
      loading="lazy"
      referrerPolicy="no-referrer"
    />
  );
}
