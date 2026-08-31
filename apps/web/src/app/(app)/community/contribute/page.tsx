"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ContributePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Contribute to ModelBridge</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Join the open-source community building the AI gateway ecosystem.
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Getting Started</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>1. Fork the repository on GitHub</p>
          <p>2. Clone and set up with Docker Compose (<code>docker compose up -d</code>)</p>
          <p>3. Run tests: <code>cd apps/api && pytest</code></p>
          <p>4. Create a feature branch and submit a pull request</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Publishing to the Marketplace</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Create a manifest JSON following the extension package format in <code>examples/extensions/</code></p>
          <p>Validate locally, then publish via <code>POST /marketplace/items</code> or CLI</p>
          <p>Submit for review — automated security checks run before publication</p>
          <Link href="/marketplace" className="underline">Browse the marketplace</Link>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Resources</CardTitle></CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p><Link href="https://github.com/suragms/modelbridge/blob/main/CONTRIBUTING.md" className="underline">CONTRIBUTING.md</Link></p>
          <p><Link href="https://github.com/suragms/modelbridge/blob/main/docs/extensions.md" className="underline">Extension documentation</Link></p>
          <p><Link href="https://github.com/suragms/modelbridge/blob/main/docs/marketplace.md" className="underline">Marketplace documentation</Link></p>
        </CardContent>
      </Card>
    </div>
  );
}
