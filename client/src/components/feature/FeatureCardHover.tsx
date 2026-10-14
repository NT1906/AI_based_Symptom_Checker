// src/components/feature/FeatureCardHover.tsx

import { Link } from "react-router-dom";

interface FeatureCardHoverProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  href?: string;
}

/**
 * A small card that shows an icon, title and description.
 * It uses Tailwind utilities to create a subtle hover‑scale and shadow effect.
 * The card is keyboard‑focusable via the surrounding <Link> (or <div> if no href).
 */
export function FeatureCardHover({
  title,
  description,
  icon,
  href,
}: FeatureCardHoverProps) {
  const inner = (
    <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm group hover:shadow-lg hover:scale-105 transition-transform duration-300 ease-out motion-reduce:transform-none motion-reduce:transition-none">
      <div className="flex items-center gap-3">
        <span className="text-2xl" aria-hidden="true">
          {icon}
        </span>
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      </div>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
    </div>
  );

  return href ? (
    <Link
      to={href}
      className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600"
    >
      {inner}
    </Link>
  ) : (
    <div className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600">
      {inner}
    </div>
  );
}
