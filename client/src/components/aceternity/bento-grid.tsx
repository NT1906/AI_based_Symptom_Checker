/**
 * @file Bento-style feature grid for the landing page.
 * Owner: Nisarg · Task: S2-NIS-20 · Issue: #321 · Requirements: NFR-06
 *
 * Adapted from Aceternity UI "Bento Grid" (ui.aceternity.com).
 * Changes: design-token colours (light and dark), lucide icons passed in by the
 * caller, semantic heading per card, a calmer hover, and rows sized by content
 * (no fixed height) so cards without a visual stay compact.
 */
import { cn } from "@/lib/utils";

/**
 * Responsive grid container.
 *
 * @param props - Grid props.
 * @param props.className - Extra classes.
 * @param props.children - Grid items.
 * @returns The grid.
 */
export function BentoGrid({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}): React.JSX.Element {
  return (
    <div
      className={cn(
        "mx-auto grid max-w-6xl grid-cols-1 gap-4 md:grid-cols-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Props for one bento card. */
type BentoGridItemProps = {
  /** Extra classes, e.g. a column span. */
  className?: string;
  /** Card title. */
  title: string;
  /** One or two sentences. */
  description: string;
  /** Decorative area at the top of the card. */
  header?: React.ReactNode;
  /** Icon shown above the title. */
  icon?: React.ReactNode;
};

/**
 * One card in the grid.
 *
 * @param props - Card content.
 * @returns The card.
 */
export function BentoGridItem({
  className,
  title,
  description,
  header,
  icon,
}: BentoGridItemProps): React.JSX.Element {
  return (
    <div
      className={cn(
        "group/bento row-span-1 flex flex-col justify-between gap-4 rounded-xl border border-border bg-card p-5 text-card-foreground shadow-xs transition duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg",
        className,
      )}
    >
      {header}
      <div className="transition duration-300 group-hover/bento:translate-x-1">
        {icon}
        <h3 className="mt-3 mb-1.5 font-semibold tracking-tight">{title}</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
