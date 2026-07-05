import { Hero } from "@/components/marketing/hero";
import { Pain } from "@/components/marketing/pain";
import { ProofStats } from "@/components/marketing/proof-stats";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { Pricing } from "@/components/marketing/pricing";
import { Comparison } from "@/components/marketing/comparison";
import { Faq } from "@/components/marketing/faq";
import { TryLiveStrip } from "@/components/marketing/try-live-strip";
import { FinalCta } from "@/components/marketing/final-cta";

export default function LandingPage() {
  return (
    <main>
      <Hero />
      <Pain />
      <ProofStats />
      <HowItWorks />
      <Pricing />
      <Comparison />
      <Faq />
      <TryLiveStrip />
      <FinalCta />
    </main>
  );
}
