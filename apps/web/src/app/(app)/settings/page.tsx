"use client";

import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const { user } = useAuth();

  const rows = [
    { label: "Email", value: user?.email ?? "—" },
    { label: "Full name", value: user?.full_name ?? "—" },
    { label: "Role", value: user?.role ?? "—" },
    { label: "Organization ID", value: user?.organization_id ?? "—" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Account and instance configuration
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Account</CardTitle>
          <CardDescription>Your sign-in details and role.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="space-y-4">
            {rows.map((r) => (
              <div key={r.label} className="flex justify-between gap-4">
                <dt className="text-sm text-[var(--muted-foreground)]">{r.label}</dt>
                <dd className="text-sm font-medium text-right break-all">{r.value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Instance</CardTitle>
          <CardDescription>
            Environment-level configuration is managed via environment variables.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-[var(--muted-foreground)]">
          <p>
            Backend URL: <code className="rounded bg-[var(--muted)] px-1">NEXT_PUBLIC_API_URL</code>
          </p>
          <p className="mt-2">
            Authentication, database and Redis settings are configured on the API
            service (see <code className="rounded bg-[var(--muted)] px-1">.env.example</code>).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
