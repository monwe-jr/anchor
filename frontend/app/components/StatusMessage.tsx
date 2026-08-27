import { AlertTriangle, Loader2, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/app/components/ui";

export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-6 text-sm text-muted">
      <Loader2 className="h-4 w-4 animate-spin text-accent" strokeWidth={2.25} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger-foreground">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2.25} />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({
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
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border px-6 py-14 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface text-faint">
        <Icon className="h-6 w-6" strokeWidth={1.75} />
      </span>
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyStateLink({
  icon: Icon,
  title,
  description,
  href,
  label,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  href: string;
  label: string;
}) {
  return (
    <EmptyState
      icon={Icon}
      title={title}
      description={description}
      action={
        <Button as="a" href={href} className="mt-1">
          {label}
        </Button>
      }
    />
  );
}
