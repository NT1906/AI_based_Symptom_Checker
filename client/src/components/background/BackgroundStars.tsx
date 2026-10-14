/**
 * @file Animated background stars component for the landing page.
 * Owner: Dimple · Task: S1-DIM-2 · Requirements: DR-01
 */

import { useEffect } from 'react';

/**
 * BackgroundStars renders a subtle animated star field.
 * It respects prefers-reduced-motion and does not intercept pointer events.
 *
 * @returns The animated star field element.
 */
export default function BackgroundStars() {
  // Generate a fixed number of star elements on mount.
  useEffect(() => {
    const container = document.getElementById('star-field');
    if (!container) return;
    const starCount = 80;
    const stars: HTMLDivElement[] = [];
    for (let i = 0; i < starCount; i++) {
      const star = document.createElement('div');
      const size = Math.random() * 2 + 1; // 1px - 3px
      const posX = Math.random() * 100; // percent
      const posY = Math.random() * 100;
      const delay = Math.random() * 5;
      star.style.position = 'absolute';
      star.style.width = `${size}px`;
      star.style.height = `${size}px`;
      star.style.borderRadius = '50%';
      star.style.background = 'rgba(255,255,255,0.8)';
      star.style.left = `${posX}%`;
      star.style.top = `${posY}%`;
      star.style.pointerEvents = 'none';
      star.style.animation = `twinkle 3s infinite ease-in-out ${delay}s`; // twinkle animation
      container.appendChild(star);
      stars.push(star);
    }
    return () => {
      stars.forEach((s) => s.remove());
    };
  }, []);

  return (
    <div
      id="star-field"
      className="fixed inset-0 -z-10 overflow-hidden pointer-events-none"
      aria-hidden="true"
    >
      {/* CSS injected via style tag */}
      <style>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0.4; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1.2); }
        }
        @media (prefers-reduced-motion: reduce) {
          #star-field div { animation: none !important; }
        }
      `}</style>
    </div>
  );
}
