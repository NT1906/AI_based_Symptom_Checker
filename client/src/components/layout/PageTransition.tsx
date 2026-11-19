/**
 * @file Gentle fade-and-rise used when a page's content appears.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 *
 * Reduced-motion users get no movement (MotionConfig reducedMotion="user").
 */
import { motion } from "motion/react";

/**
 * Animate children in on mount.
 *
 * @param props - Component props.
 * @param props.children - Content to reveal.
 * @param props.className - Optional extra classes.
 * @returns The animated wrapper.
 */
export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}): React.JSX.Element {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
