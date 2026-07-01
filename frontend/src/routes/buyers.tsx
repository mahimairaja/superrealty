import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { getBuyers, type BuyerSummary } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

function criteriaChips(criteria?: Record<string, unknown> | null): string[] {
  if (!criteria) return [];
  const out: string[] = [];
  if (criteria.area) out.push(String(criteria.area));
  if (criteria.minBeds) out.push(`${criteria.minBeds}+ bed`);
  if (criteria.maxPrice) out.push(`under $${Number(criteria.maxPrice).toLocaleString()}`);
  return out;
}

export default function Buyers() {
  const [buyers, setBuyers] = useState<BuyerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    getBuyers()
      .then((b) => active && setBuyers(b))
      .catch(() => active && setError(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  function reload() {
    setLoading(true);
    setError(false);
    getBuyers()
      .then(setBuyers)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Everyone your assistant has remembered across calls, scoped to your
        agency.
      </p>

      {loading ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          Loading buyers...
        </p>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="text-sm text-muted-foreground">
              Could not load your buyers.
            </p>
            <Button variant="outline" size="sm" onClick={reload}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : buyers.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <span className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Users className="size-5" />
            </span>
            <p className="text-sm font-medium">No buyers yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              When a buyer calls and shares what they want, the assistant
              remembers them here for your follow-up.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {buyers.map((b, i) => (
            <Card key={b.phone ?? i} className="gap-3">
              <CardContent className="space-y-2">
                <div className="text-sm font-medium">{b.name ?? "Buyer"}</div>
                {b.phone && (
                  <div className="font-mono text-xs tabular-nums text-muted-foreground">
                    {b.phone}
                  </div>
                )}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {criteriaChips(b.criteria).map((c) => (
                    <Badge key={c} variant="muted">
                      {c}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
