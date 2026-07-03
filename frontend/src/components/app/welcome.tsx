import { useState } from "react";
import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

// The buyer enters a number before connecting so the assistant can recognize a returning
// caller from the first word (a web call has no caller ID). Any digits work: it is only a key
// for remembering this caller, not verified. Optional, so it never blocks starting the call.
export function Welcome({ onStart }: { onStart: (phone: string) => void }) {
  const [phone, setPhone] = useState("");
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
              Click start, allow your microphone, and speak. It answers in the
              realtor's name and remembers you the next time you call.
            </p>
          </div>
          <div className="w-full space-y-1.5 text-left">
            <label htmlFor="buyer-phone" className="text-sm font-medium">
              Your phone number
            </label>
            <Input
              id="buyer-phone"
              type="tel"
              inputMode="numeric"
              autoComplete="tel"
              placeholder="e.g. 519 555 0142"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Enter any 10 digits. We use it to remember you, so next time the
              assistant greets you by name.
            </p>
          </div>
          <Button
            size="lg"
            className="w-full"
            onClick={() => onStart(phone)}
          >
            Start conversation
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
