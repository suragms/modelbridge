"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  Activity,
  BarChart3,
  Boxes,
  ChevronDown,
  Code2,
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
  Webhook,
  Plug,
  Zap,
  Palette,
  Shield,
  DollarSign,
  Search,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { OrgSwitcher } from "@/components/org-switcher";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/playground", label: "Playground", icon: FlaskConical },
      { href: "/analytics", label: "Analytics", icon: BarChart3 },
    ],
  },
  {
    label: "AI Gateway",
    items: [
      { href: "/providers", label: "Providers", icon: Server },
      { href: "/models", label: "Models", icon: Boxes },
      { href: "/routing", label: "Routing", icon: GitBranch },
      { href: "/api-keys", label: "API Keys", icon: KeyRound },
      { href: "/requests", label: "Requests", icon: Activity },
    ],
  },
  {
    label: "Platform",
    items: [
      { href: "/agents", label: "Agents", icon: Bot },
      { href: "/studio", label: "AI Studio", icon: Palette },
      { href: "/quality", label: "Quality", icon: Shield },
      { href: "/finops", label: "FinOps", icon: DollarSign },
      { href: "/workflows", label: "Workflows", icon: Workflow },
      { href: "/governance", label: "Governance", icon: ShieldCheck },
    ],
  },
  {
    label: "Extensions",
    items: [
      { href: "/extensions", label: "Extensions", icon: Puzzle },
      { href: "/templates", label: "Templates", icon: Layers },
      { href: "/marketplace", label: "Marketplace", icon: Layers },
    ],
  },
  {
    label: "Infrastructure",
    items: [
      { href: "/enterprise", label: "Enterprise", icon: Building2 },
      { href: "/fleet", label: "Fleet", icon: Network },
      { href: "/cloud", label: "Cloud", icon: Server },
      { href: "/intelligence", label: "Intelligence", icon: Activity },
    ],
  },
  {
    label: "Developer",
    items: [
      { href: "/developers", label: "API Reference", icon: Code2 },
      { href: "/webhooks", label: "Webhooks", icon: Webhook },
      { href: "/integrations", label: "Integrations", icon: Plug },
      { href: "/automations", label: "Automations", icon: Zap },
    ],
  },
];

const BOTTOM_NAV: NavItem[] = [
  { href: "/community/contribute", label: "Contribute", icon: Code2 },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const handleLogout = () => {
    logout();
    router.replace("/");
  };

  const toggleGroup = (label: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  // Filter nav items by search
  const allFlatItems = NAV_GROUPS.flatMap((g) => g.items).concat(BOTTOM_NAV);
  const isSearching = searchQuery.length > 0;
  const filteredGroups = isSearching
    ? [
        {
          label: "Search Results",
          items: allFlatItems.filter(
            (item) =>
              item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
              item.href.toLowerCase().includes(searchQuery.toLowerCase())
          ),
        },
      ]
    : NAV_GROUPS;

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  return (
    <aside className="flex h-full w-64 flex-col border-r border-[var(--border)] bg-[var(--card)]">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-[var(--border)] px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand-gradient)] shadow-sm">
            <Boxes className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-bold tracking-tight">ModelBridge</span>
        </Link>
      </div>

      {/* Search */}
      <div className="px-3 pt-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--muted-foreground)]" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 w-full rounded-md border border-[var(--border)] bg-[var(--muted)]/50 pl-8 pr-3 text-xs placeholder:text-[var(--muted-foreground)] focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)]/30"
          />
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        {filteredGroups.map((group) => {
          const isCollapsed = collapsedGroups.has(group.label) && !isSearching;
          return (
            <div key={group.label} className="mb-2">
              <button
                onClick={() => toggleGroup(group.label)}
                className="flex w-full items-center justify-between px-2 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted-foreground)]/70 hover:text-[var(--muted-foreground)] transition-colors"
              >
                {group.label}
                {!isSearching && (
                  <ChevronDown
                    className={cn(
                      "h-3 w-3 transition-transform duration-200",
                      isCollapsed && "-rotate-90"
                    )}
                  />
                )}
              </button>
              {!isCollapsed && (
                <div className="mt-0.5 space-y-0.5">
                  {group.items.map((item) => {
                    const active = isActive(item.href);
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "group flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition-all duration-150",
                          active
                            ? "bg-[var(--brand-gradient-soft)] text-[var(--primary)]"
                            : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]/80 hover:text-[var(--foreground)]"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-4 w-4 shrink-0 transition-colors",
                            active
                              ? "text-[var(--primary)]"
                              : "text-[var(--muted-foreground)] group-hover:text-[var(--foreground)]"
                          )}
                        />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-[var(--border)] p-3">
        <OrgSwitcher />
        <div className="mt-2 flex items-center gap-2.5 rounded-lg px-2.5 py-2">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--brand-gradient)] text-[10px] font-bold text-white">
            {user?.email?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="mt-1 flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/80 hover:text-[var(--foreground)]"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
