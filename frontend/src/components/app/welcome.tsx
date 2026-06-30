import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function Welcome({ onStart }: { onStart: () => void }) {
  return (
    <div className="grid min-h-[calc(100svh-3.5rem)] place-items-center p-6">
      <Card className="w-full max-w-md text-center">
        <CardContent className="flex flex-col items-center gap-5 py-2">
          <span className="flex size-14 items-center justify-center rounded-full bg-accent text-primary">
            <Mic className="size-7" />
          </span>
          <div className="space-y-1.5">
            <h1 className="text-xl font-semibold tracking-tight">
              Talk to the assistant
            </h1>
            <p className="text-sm text-muted-foreground">
              Click start, allow your microphone, and speak. It answers in your
              name and remembers you the next time you call.
            </p>
          </div>
          <Button size="lg" className="w-full" onClick={onStart}>
            Start conversation
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
