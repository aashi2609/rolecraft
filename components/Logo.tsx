import Link from 'next/link';
import { cn } from '@/lib/utils';

interface LogoProps {
  /** Pass null to render without a link */
  href?: string | null;
  className?: string;
  markClassName?: string;
  wordmarkClassName?: string;
  showWordmark?: boolean;
  showMark?: boolean;
}

/** Blue geometric mark + RoleCraft wordmark */
export function Logo({
  href = '/',
  className,
  markClassName,
  wordmarkClassName,
  showWordmark = true,
  showMark = true,
}: LogoProps) {
  const content = (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      {showMark && (
        <svg
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={cn('h-8 w-8 shrink-0', markClassName)}
          aria-hidden
        >
          <rect width="32" height="32" rx="8" className="fill-primary" />
          <path
            d="M9 22V10h6.2c2.85 0 4.55 1.55 4.55 3.85 0 1.55-.85 2.7-2.2 3.25L22 22h-3.15l-3.9-4.55H12.2V22H9zm3.2-7.15h2.85c1.35 0 2.1-.65 2.1-1.75s-.75-1.7-2.1-1.7H12.2v3.45z"
            className="fill-primary-foreground"
          />
        </svg>
      )}
      {showWordmark && (
        <span
          className={cn(
            'font-display text-lg font-bold tracking-tight text-ink',
            wordmarkClassName
          )}
        >
          RoleCraft
        </span>
      )}
    </span>
  );

  if (href === null) return content;
  return (
    <Link
      href={href || '/'}
      className="inline-flex focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
    >
      {content}
    </Link>
  );
}
