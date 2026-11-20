/**
 * @file Headline that fades its words in one after another.
 * Owner: Nisarg · Task: S2-NIS-20 · Issue: #321 · Requirements: NFR-06
 *
 * Adapted from Aceternity UI "Text Generate Effect" (ui.aceternity.com).
 * Changes: inherits colour and size from the parent (works in dark mode),
 * renders inline so it can live inside an <h1>, and exposes the full text to
 * screen readers once instead of word by word.
 */
import { useEffect } from "react";
import { motion, stagger, useAnimate } from "motion/react";
import { cn } from "@/lib/utils";

/** Props for TextGenerateEffect. */
type TextGenerateEffectProps = {
  /** The sentence to reveal. */
  words: string;
  /** Extra classes for the wrapper. */
  className?: string;
  /** Blur words in as well as fading them. */
  filter?: boolean;
  /** Seconds each word takes to appear. */
  duration?: number;
};

/**
 * Reveal a sentence word by word.
 *
 * @param props - Effect options.
 * @returns The animated text.
 */
export function TextGenerateEffect({
  words,
  className,
  filter = true,
  duration = 0.5,
}: TextGenerateEffectProps): React.JSX.Element {
  const [scope, animate] = useAnimate();
  const list = words.split(" ");

  useEffect(() => {
    void animate(
      "span[data-word]",
      { opacity: 1, filter: filter ? "blur(0px)" : "none" },
      { duration, delay: stagger(0.08) },
    );
  }, [animate, duration, filter, words]);

  return (
    <span className={cn("inline", className)}>
      <span className="sr-only">{words}</span>
      <span ref={scope} aria-hidden="true">
        {list.map((word, index) => (
          <motion.span
            key={`${word}-${index}`}
            data-word
            className="inline-block opacity-0"
            style={{ filter: filter ? "blur(8px)" : "none" }}
          >
            {word}
            {index < list.length - 1 ? " " : ""}
          </motion.span>
        ))}
      </span>
    </span>
  );
}
