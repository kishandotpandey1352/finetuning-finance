"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { AppMode } from "@/types";

type SidebarProps = {
  displayName: string;
  mode: AppMode;
  onLogout: () => void;
};

const navItems = [
  {
    href: "/dashboard",
    label: "Dashboard",
    action: "Open",
    color: "cyan",
  },
  {
    href: "/compare",
    label: "Compare",
    action: "Go",
    color: "violet",
  },
  {
    href: "/history",
    label: "History",
    action: "Go",
    color: "emerald",
  },
  {
    href: "/login",
    label: "Login",
    action: "Go",
    color: "amber",
  },
] as const;

const navColorClasses = {
  cyan: {
    active: "border-cyan-300/70 bg-cyan-300/15 text-cyan-50 shadow-[0_0_32px_rgba(103,232,249,0.14)]",
    inactive: "border-cyan-300/20 bg-cyan-300/5 text-slate-300 hover:border-cyan-300/50 hover:bg-cyan-300/10 hover:text-cyan-50",
    action: "text-cyan-200",
    card: "border-cyan-300/30 bg-cyan-300/10",
    title: "text-cyan-200",
  },
  violet: {
    active: "border-violet-300/70 bg-violet-300/15 text-violet-50 shadow-[0_0_32px_rgba(196,181,253,0.14)]",
    inactive: "border-violet-300/20 bg-violet-300/5 text-slate-300 hover:border-violet-300/50 hover:bg-violet-300/10 hover:text-violet-50",
    action: "text-violet-200",
    card: "border-violet-300/30 bg-violet-300/10",
    title: "text-violet-200",
  },
  emerald: {
    active: "border-emerald-300/70 bg-emerald-300/15 text-emerald-50 shadow-[0_0_32px_rgba(110,231,183,0.14)]",
    inactive: "border-emerald-300/20 bg-emerald-300/5 text-slate-300 hover:border-emerald-300/50 hover:bg-emerald-300/10 hover:text-emerald-50",
    action: "text-emerald-200",
    card: "border-emerald-300/30 bg-emerald-300/10",
    title: "text-emerald-200",
  },
  amber: {
    active: "border-amber-300/70 bg-amber-300/15 text-amber-50 shadow-[0_0_32px_rgba(252,211,77,0.12)]",
    inactive: "border-amber-300/20 bg-amber-300/5 text-slate-300 hover:border-amber-300/50 hover:bg-amber-300/10 hover:text-amber-50",
    action: "text-amber-200",
    card: "border-amber-300/30 bg-amber-300/10",
    title: "text-amber-200",
  },
};

export function Sidebar({ displayName, mode, onLogout }: SidebarProps) {
  const pathname = usePathname();

  const activeNavItem = navItems.find((item) => pathname === item.href) ?? navItems[0];
  const activeColor = navColorClasses[activeNavItem.color];

  return (
  <aside className="soft-panel p-5 sm:p-6">
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-xs uppercase tracking-[0.32em] text-cyan-200/70">
          LLM Studio
        </p>
        <h2 className="mt-3 text-2xl font-semibold text-white">
          {displayName}
        </h2>
        <p className="mt-2 text-sm text-slate-300">
          JWT-ready frontend for the secure inference gateway.
        </p>
      </div>

      <nav className="grid w-full grid-cols-4 gap-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const color = navColorClasses[item.color];

          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "group flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-semibold transition",
                isActive ? color.active : color.inactive,
              ].join(" ")}
            >
              <span>{item.label}</span>
              <span
                className={[
                  "text-[10px] uppercase tracking-[0.28em]",
                  isActive ? color.action : "text-slate-500 group-hover:" + color.action,
                ].join(" ")}
              >
                {item.action}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
        <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
          Active mode
        </p>
        <p className="mt-2 text-lg font-semibold capitalize text-white">
          {mode}
        </p>
        <p className="mt-1 text-sm text-slate-400">
          Basic, Premium, and Compare workflows are ready.
        </p>
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">
          Security
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          Tokens are stored locally and forwarded as Authorization plus
          X-API-Key for gateway compatibility.
        </p>
      </div>

      <button
        type="button"
        onClick={onLogout}
        className="self-start text-sm font-semibold text-slate-400 transition hover:text-white"
      >
        Sign out
      </button>
    </div>
  </aside>
);
}