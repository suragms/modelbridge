"use client";

import { useOrganizations } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { Select } from "@/components/ui/select";

export function OrgSwitcher() {
  const { activeOrgId, user, switchOrganization } = useAuth();
  const orgsQuery = useOrganizations();
  const orgs = (orgsQuery.data ?? []) as Array<{ id: string; name: string }>;
  const current = activeOrgId ?? user?.organization_id ?? "";

  if (orgs.length <= 1) {
    const name = orgs[0]?.name ?? "Organization";
    return <span className="truncate text-xs text-[var(--muted-foreground)]">{name}</span>;
  }

  return (
    <Select
      value={current}
      onChange={async (e) => {
        const id = e.target.value;
        if (id && id !== current) await switchOrganization(id);
      }}
      className="h-8 w-full text-xs"
    >
      {orgs.map((o) => (
        <option key={o.id} value={o.id}>
          {o.name}
        </option>
      ))}
    </Select>
  );
}
