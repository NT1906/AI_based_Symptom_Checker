/**
 * @file Ambient spotlight beams for the landing hero.
 * Owner: Nisarg · Task: S2-NIS-20 · Issue: #321 · Requirements: NFR-06
 *
 * Adapted from Aceternity UI "Spotlight (new)" (ui.aceternity.com, free to use).
 * Changes: teal tint from the design tokens, gentler motion, decorative only
 * (aria-hidden), and no movement for reduced-motion users (MotionConfig).
 */
import { motion } from "motion/react";

/** Props for Spotlight. */
type SpotlightProps = {
  /** Seconds for one sweep of the beams. */
  duration?: number;
  /** How far the beams drift sideways, in pixels. */
  xOffset?: number;
};

const BEAM = "oklch(0.75 0.1 190 / 0.10)";
const BEAM_SOFT = "oklch(0.75 0.1 190 / 0.05)";

const first = `radial-gradient(68.54% 68.72% at 55.02% 31.46%, ${BEAM} 0, ${BEAM_SOFT} 50%, transparent 80%)`;
const second = `radial-gradient(50% 50% at 50% 50%, ${BEAM} 0, ${BEAM_SOFT} 80%, transparent 100%)`;

/**
 * Two soft beams that sway slowly from the top corners.
 *
 * @param props - Spotlight options.
 * @returns The decorative layer.
 */
export function Spotlight({ duration = 9, xOffset = 80 }: SpotlightProps): React.JSX.Element {
  const sides = [
    { side: "left-0", rotate: -45, drift: xOffset, origin: "origin-top-left" },
    { side: "right-0", rotate: 45, drift: -xOffset, origin: "origin-top-right" },
  ] as const;
  return (
    <motion.div
      aria-hidden="true"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1.5 }}
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {sides.map(({ side, rotate, drift, origin }) => (
        <motion.div
          key={side}
          animate={{ x: [0, drift, 0] }}
          transition={{ duration, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
          className={`absolute top-0 ${side} h-full w-full`}
        >
          <div
            className={`absolute top-0 ${side}`}
            style={{
              transform: `translateY(-350px) rotate(${rotate}deg)`,
              background: first,
              width: 560,
              height: 1380,
            }}
          />
          <div
            className={`absolute top-0 ${side} ${origin}`}
            style={{
              transform: `rotate(${rotate}deg) translate(${rotate < 0 ? "5%" : "-5%"}, -50%)`,
              background: second,
              width: 240,
              height: 1380,
            }}
          />
        </motion.div>
      ))}
    </motion.div>
  );
}
