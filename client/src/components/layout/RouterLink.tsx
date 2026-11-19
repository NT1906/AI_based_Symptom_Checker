/**
 * @file Link that works with or without a router around it.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 *
 * Inside the app it is a client-side `Link` (no reload, so in-memory consent and
 * assessment state survive). In isolated component tests it falls back to `<a>`.
 */
import { Link, useInRouterContext } from "react-router-dom";

/** Props for RouterLink. */
type RouterLinkProps = Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  /** Destination path. */
  to: string;
};

/**
 * Router-aware link.
 *
 * @param props - Link props.
 * @returns A `Link` inside a router, otherwise a plain anchor.
 */
export function RouterLink({ to, ...rest }: RouterLinkProps): React.JSX.Element {
  const inRouter = useInRouterContext();
  return inRouter ? <Link to={to} {...rest} /> : <a href={to} {...rest} />;
}
