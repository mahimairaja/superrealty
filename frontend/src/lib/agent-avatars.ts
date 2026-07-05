// Reusable agent avatar set (8 originals) for visualizing the multi-agent
// roster. Deterministically map an agent id (or any stable key) to one avatar
// so a given agent always shows the same face across the app.
import a1 from "@/assets/agents/agent-1.svg";
import a2 from "@/assets/agents/agent-2.svg";
import a3 from "@/assets/agents/agent-3.svg";
import a4 from "@/assets/agents/agent-4.svg";
import a5 from "@/assets/agents/agent-5.svg";
import a6 from "@/assets/agents/agent-6.svg";
import a7 from "@/assets/agents/agent-7.svg";
import a8 from "@/assets/agents/agent-8.svg";

export const AGENT_AVATARS: readonly string[] = [a1, a2, a3, a4, a5, a6, a7, a8];

/** Stable FNV-1a hash so the same key always maps to the same avatar. */
function hashKey(key: string): number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Pick a deterministic avatar URL for an agent id (or any stable key). */
export function pickByAgentId(agentId: string): string {
  if (!agentId) return AGENT_AVATARS[0];
  return AGENT_AVATARS[hashKey(agentId) % AGENT_AVATARS.length];
}
