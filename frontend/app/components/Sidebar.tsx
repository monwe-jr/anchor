"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Anchor, FileText, Layers, MessageCircle, UploadCloud } from "lucide-react";

const LINKS = [
  { href: "/upload", label: "Upload", icon: UploadCloud },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/review", label: "Review", icon: Layers },
  { href: "/chat", label: "Chat", icon: MessageCircle },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-border bg-sidebar px-3 py-5">
      <div className="flex items-center gap-2 px-2 pb-6">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-accent">
          <Anchor className="h-4.5 w-4.5" strokeWidth={2.25} />
        </span>
        <span className="text-base font-semibold tracking-tight text-foreground">Anchor</span>
      </div>

      <nav className="flex flex-col gap-1">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150 ${
                active
                  ? "bg-accent/15 font-medium text-accent"
                  : "text-muted hover:bg-surface hover:text-foreground"
              }`}
            >
              <Icon
                className={`h-4 w-4 shrink-0 ${
                  active ? "text-accent" : "text-faint group-hover:text-foreground"
                }`}
                strokeWidth={2}
              />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
