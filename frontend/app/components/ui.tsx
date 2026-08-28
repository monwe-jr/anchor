import Link from "next/link";
import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export function PageHeader({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent">
          <Icon className="h-5 w-5" strokeWidth={2} />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
          {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function Card({
  children,
  className = "",
  interactive = false,
  ...props
}: {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
} & ComponentPropsWithoutRef<"div">) {
  return (
    <div
      className={`rounded-2xl border border-border bg-surface shadow-soft ${
        interactive
          ? "transition-colors duration-150 hover:border-border-strong hover:bg-surface-hover"
          : ""
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardLink({
  href,
  children,
  className = "",
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`block rounded-2xl border border-border bg-surface shadow-soft transition-all duration-150 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-hover hover:shadow-soft-hover ${className}`}
    >
      {children}
    </Link>
  );
}

const buttonVariants = {
  primary:
    "bg-accent text-accent-foreground hover:bg-accent-hover disabled:hover:bg-accent",
  secondary:
    "border border-border bg-surface text-foreground hover:border-border-strong hover:bg-surface-hover",
  ghost: "text-muted hover:bg-surface hover:text-foreground",
};

type ButtonProps<T extends ElementType> = {
  as?: T;
  variant?: keyof typeof buttonVariants;
  icon?: LucideIcon;
  className?: string;
  children?: ReactNode;
} & Omit<ComponentPropsWithoutRef<T>, "as" | "className" | "children">;

export function Button<T extends ElementType = "button">({
  as,
  variant = "primary",
  icon: Icon,
  className = "",
  children,
  ...props
}: ButtonProps<T>) {
  const Component = as || "button";
  return (
    <Component
      className={`inline-flex w-fit items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${buttonVariants[variant]} ${className}`}
      {...props}
    >
      {Icon && <Icon className="h-4 w-4" strokeWidth={2.25} />}
      {children}
    </Component>
  );
}

const badgeVariants: Record<string, string> = {
  neutral: "bg-border/60 text-muted",
  accent: "bg-accent/15 text-accent",
  success: "bg-success/15 text-success",
  danger: "bg-danger/15 text-danger-foreground",
};

export function Badge({
  children,
  variant = "neutral",
  className = "",
}: {
  children: ReactNode;
  variant?: keyof typeof badgeVariants;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium capitalize ${badgeVariants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Stat({
  value,
  label,
  className = "",
}: {
  value: ReactNode;
  label: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <span className="text-4xl font-bold leading-none tracking-tight text-foreground">
        {value}
      </span>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}

const progressColors = {
  accent: "bg-accent",
  success: "bg-success",
  danger: "bg-danger",
};

export function ProgressBar({
  percent,
  color = "accent",
  className = "",
}: {
  percent: number;
  color?: keyof typeof progressColors;
  className?: string;
}) {
  const clamped = Math.min(100, Math.max(0, percent));
  return (
    <div className={`h-1.5 w-full overflow-hidden rounded-full bg-border/60 ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-300 ${progressColors[color]}`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
