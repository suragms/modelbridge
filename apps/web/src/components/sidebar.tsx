"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  BarChart3,
  Boxes,
  FlaskConical,
  GitBranch,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Bot,
  Workflow,
  Layers,
  Puzzle,
  Building2,
  Network,
  Server,
  ShieldCheck,
  Settings as SettingsIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { OrgSwitcher } from "@/components/org-switcher";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/playground", label: "Playground", icon: FlaskConical },
  { href: "/providers", label: "Providers", icon: Server },
  { href: "/models", label: "Models", icon: Boxes },
  { href: "/routing", label: "Routing", icon: GitBranch },
  { href: "/api-keys", label: "API Keys", icon: KeyRound },
  { href: "/requests", label: "Requests", icon: Activity },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/governance", label: "Governance", icon: ShieldCheck },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/extensions", label: "Extensions", icon: Puzzle },
  { href: "/templates", label: "Templates", icon: Layers },
  { href: "/enterprise", label: "Enterprise", icon: Building2 },
  { href: "/fleet", label: "Fleet", icon: Network },
  { href: "/cloud", label: "Cloud", icon: Server },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.replace("/");
  };

  return (
    <aside className="flex h-full w-60 flex-col border-r border-[var(--border)] bg-[var(--card)]">
      <div className="flex h-16 items-center gap-2 border-b border-[var(--border)] px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)]">
          <Boxes className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold">ModelBridge</span>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-[var(--muted)] text-[var(--foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]/60 hover:text-[var(--foreground)]"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--border)] p-3">
        <div className="mb-2 px-3">
          <OrgSwitcher />
        </div>
        <div className="mb-2 px-3 text-xs text-[var(--muted-foreground)]">
          {user?.email}
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-[var(--muted-foreground)] hover:bg-[var(--muted)]/60 hover:text-[var(--foreground)]"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
