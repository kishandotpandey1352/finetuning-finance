"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { AppMode } from "@/types";

interface SidebarProps {
  displayName: string;
  mode: AppMode;
  onLogout?: () => void;
}

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/compare", label: "Compare" },
  { href: "/history", label: "History" },
  { href: "/login", label: "Login" },
];

export function Sidebar({ displayName, mode, onLogout }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full flex-col justify-between rounded-[32px] border border-white/10 bg-panel/80 p-5 shadow-halo backdrop-blur-xl">
      <div className="space-y-6">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-cyan-200/70">Finance LLM Studio</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{displayName}</h2>
          <p className="mt-1 text-sm text-slate-400">JWT-ready frontend for the secure inference gateway.</p>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Active mode</p>
          <p className="mt-2 text-lg font-semibold text-white">{mode}</p>
          <p className="mt-1 text-sm text-slate-400">Basic, Premium, and Compare workflows are ready.</p>
        </div>

        <nav className="space-y-2">
          {links.map((link) => {
            const active = pathname === link.href;

            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-sm transition ${active ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100" : "border-white/8 bg-white/0 text-slate-300 hover:border-white/15 hover:bg-white/5 hover:text-white"}`}
              >
                <span>{link.label}</span>
                <span className="text-xs uppercase tracking-[0.2em] text-slate-500">{active ? "Open" : "Go"}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="space-y-3">
        <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Security</p>
          <p className="mt-2">Tokens are stored locally and forwarded as `Authorization` plus `X-API-Key` for gateway compatibility.</p>
        </div>
        {onLogout ? (
          <button
            type="button"
            onClick={onLogout}
            className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10"
          >
            Sign out
          </button>
        ) : null}
      </div>
    </aside>
  );
}