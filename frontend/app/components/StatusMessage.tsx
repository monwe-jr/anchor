export function Loading({ label = "Loading..." }: { label?: string }) {
  return <p className="text-sm text-black/60 dark:text-white/60">{label}</p>;
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
      {message}
    </div>
  );
}
