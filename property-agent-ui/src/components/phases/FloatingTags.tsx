// Floating chips for the profiling page (Phase 1.5).
//
// Each chip surfaces a Phase 1 input value the user typed/picked, so the
// agent's "memory" of what it knows is visible while semantic alignment
// runs in the background.
//
// Collision contract (NON-NEGOTIABLE):
//   1. Chips MUST NOT enter the centered safe zone (headline / sub-copy
//      / progress bars).
//   2. Chips MUST NOT visually collide with each other, even with the
//      longest label and full drift amplitude.
//
// Strategy:
//   - All chips anchored to the left OR right edge (never the center).
//   - Per side, chips are distributed across non-overlapping vertical
//     bands. Each band reserves >= 22% of the host height; chip is ~28px
//     tall + drift amplitude ~8px, so even at viewport=700px the gap
//     between consecutive band centers (~150px) >> chip footprint.
//   - Each chip is clamped to max-width 38% of the host so its right/left
//     edge cannot reach the center safe zone.
//   - Motion uses 4 irregular drift variants with prime-ish durations and
//     unique delays → non-periodic on human timescales.
//   - On viewports narrower than MIN_WIDTH_PX the safe zone + chip
//     margins do not fit honestly, so chips are hidden.
//
// Phase 1.5 update: chips now reflect *user input* from Phase 1 instead
// of decorative-only labels. A chip is hidden entirely when the
// underlying field is empty, so the user never sees a placeholder for
// a value they did not actually supply.

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import type { AgentStyle, Gender, Identity } from "@/lib/types";

type DriftVariant = "a" | "b" | "c" | "d";

interface Anchor {
  key: string;
  label: string;
  // Exactly one of left/right is set (chips always edge-anchored).
  side: "left" | "right";
  edgeOffset: string; // e.g. "4%"
  top: string;        // vertical center expressed as top %
  delay: string;
  duration: string;
  variant: DriftVariant;
  emphasis?: boolean;
}

// Below this viewport width the safe zone + chip margins do not fit.
const MIN_WIDTH_PX = 880;

const IDENTITY_LABEL: Record<Identity, string> = {
  first_time_buyer: "First-time buyer",
  investor: "Investor",
  upgrader: "Upgrader",
};
const GENDER_LABEL: Record<Gender, string> = {
  female: "Female",
  male: "Male",
  prefer_not_to_say: "Undisclosed",
};
const STYLE_LABEL: Record<AgentStyle, string> = {
  Professional: "Professional",
  Friendly: "Friendly",
  Enthusiastic: "Enthusiastic",
};

function fmtBudget(n: number | undefined): string | null {
  if (!n || n <= 0) return null;
  return `RM ${n.toLocaleString("en-MY")}`;
}

function trimText(v: string | undefined, max = 28): string | null {
  const t = (v ?? "").trim();
  if (!t) return null;
  return t.length > max ? `${t.slice(0, max - 1)}…` : t;
}

// A non-overlapping band layout with up to 4 slots per side.
const LEFT_TOPS = ["14%", "44%", "74%"];
const RIGHT_TOPS = ["12%", "36%", "60%", "84%"];

const VARIANTS: DriftVariant[] = ["a", "b", "c", "d"];

interface ChipSpec {
  key: string;
  label: string;
  emphasis?: boolean;
}

export function FloatingTags() {
  const [visible, setVisible] = useState(false);
  const phase1 = useAppStore((s) => s.phase1Form);

  useEffect(() => {
    const check = () => setVisible(window.innerWidth >= MIN_WIDTH_PX);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!visible) return null;

  // Build chip specs from the user's actual Phase 1 input. Anything the
  // user did not supply is skipped — never shown as "—".
  const specs: ChipSpec[] = [];

  const budget = fmtBudget(phase1?.budget);
  if (budget) specs.push({ key: "budget", label: `BUDGET · ${budget}`, emphasis: true });

  const target = trimText(phase1?.target);
  if (target) specs.push({ key: "target", label: `TARGET · ${target.toUpperCase()}`, emphasis: true });

  if (phase1?.identity) {
    specs.push({
      key: "identity",
      label: `IDENTITY · ${IDENTITY_LABEL[phase1.identity].toUpperCase()}`,
      emphasis: true,
    });
  }

  if (phase1?.agent_style) {
    specs.push({
      key: "agent_style",
      label: `STYLE · ${STYLE_LABEL[phase1.agent_style].toUpperCase()}`,
    });
  }

  if (phase1?.gender) {
    specs.push({
      key: "gender",
      label: `GENDER · ${GENDER_LABEL[phase1.gender].toUpperCase()}`,
    });
  }

  const desc = trimText(phase1?.description, 32);
  if (desc) specs.push({ key: "description", label: `“${desc}”` });

  // Distribute specs across left/right bands. Alternate sides so the
  // composition stays balanced even when only some chips are present.
  const anchors: Anchor[] = [];
  let leftIdx = 0;
  let rightIdx = 0;
  specs.forEach((spec, i) => {
    const side: "left" | "right" =
      (i % 2 === 0 && leftIdx < LEFT_TOPS.length) || rightIdx >= RIGHT_TOPS.length
        ? "left"
        : "right";
    const top =
      side === "left"
        ? LEFT_TOPS[Math.min(leftIdx++, LEFT_TOPS.length - 1)]
        : RIGHT_TOPS[Math.min(rightIdx++, RIGHT_TOPS.length - 1)];
    anchors.push({
      key: spec.key,
      label: spec.label,
      side,
      edgeOffset: side === "left" ? "5%" : "5%",
      top,
      delay: `${(i * 0.37) % 2.4}s`,
      duration: `${6.7 + ((i * 1.3) % 3.5)}s`,
      variant: VARIANTS[i % VARIANTS.length],
      emphasis: spec.emphasis,
    });
  });

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {anchors.map((a) => (
        // Outer wrapper owns the absolute anchor + vertical centering.
        // Inner element owns the drift animation, so the two transforms
        // don't compete (keyframes would otherwise overwrite translateY).
        <div
          key={a.key}
          className="absolute max-w-[38%]"
          style={{
            [a.side]: a.edgeOffset,
            top: a.top,
            transform: "translateY(-50%)",
          }}
        >
          <div
            className={[
              "drift truncate whitespace-nowrap rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] backdrop-blur-sm",
              `drift-${a.variant}`,
              a.emphasis
                ? "border-primary/40 bg-primary/[0.06] text-foreground/80"
                : "border-border/60 bg-surface/70 text-muted-foreground",
            ].join(" ")}
            style={{
              animationDelay: a.delay,
              animationDuration: a.duration,
            }}
          >
            {a.label}
          </div>
        </div>
      ))}
    </div>
  );
}
