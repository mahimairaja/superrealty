// Lightweight memory-graph motif for the hero. Pure SVG so it renders in jsdom and
// needs no tenant data (the live react-force-graph is canvas-based and tenant-scoped,
// so it does not belong on the public page).
const NODES = [
  { cx: 60, cy: 60, r: 10, label: "buyer" },
  { cx: 160, cy: 40, r: 8 },
  { cx: 250, cy: 70, r: 12, label: "home" },
  { cx: 110, cy: 140, r: 8 },
  { cx: 210, cy: 160, r: 10, label: "home" },
  { cx: 60, cy: 190, r: 7 },
];
const LINKS = [
  [0, 1],
  [1, 2],
  [0, 3],
  [3, 4],
  [1, 4],
  [3, 5],
];

export function GraphMotif({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 320 220"
      className={className}
      role="img"
      aria-label="A memory graph connecting buyers to homes"
    >
      <g stroke="currentColor" strokeWidth={1.5} className="text-border">
        {LINKS.map(([a, b], i) => (
          <line
            key={i}
            x1={NODES[a].cx}
            y1={NODES[a].cy}
            x2={NODES[b].cx}
            y2={NODES[b].cy}
          />
        ))}
      </g>
      {NODES.map((n, i) => (
        <circle
          key={i}
          cx={n.cx}
          cy={n.cy}
          r={n.r}
          className={n.label ? "fill-primary" : "fill-muted-foreground/40"}
        />
      ))}
    </svg>
  );
}
