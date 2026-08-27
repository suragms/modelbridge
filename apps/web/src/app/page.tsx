import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  Cpu,
  GitFork,
  KeyRound,
  Lock,
  Plug,
  Shield,
  Server,
  Workflow,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Plug,
    title: "One OpenAI-compatible API",
    description:
      "Use your existing OpenAI SDKs and tools. ModelBridge exposes a single /v1/chat/completions endpoint across all providers.",
  },
  {
    icon: Server,
    title: "Cloud & local providers",
    description:
      "Connect cloud AI services and local models running on your own hardware through a unified interface.",
  },
  {
    icon: Workflow,
    title: "Intelligent routing (coming soon)",
    description:
      "Route each request to the best provider by cost, speed, quality, or privacy. Automatic fallback when a provider is down.",
  },
  {
    icon: KeyRound,
    title: "API key management",
    description:
      "Issue scoped API keys, rotate and revoke them, and authenticate every request securely.",
  },
  {
    icon: Lock,
    title: "Self-hosted",
    description:
      "Run ModelBridge entirely on your own infrastructure. Your prompts and keys never leave your control.",
  },
  {
    icon: Shield,
    title: "Secure by design",
    description:
      "Passwords hashed, provider secrets encrypted, API keys stored as hashes only.",
  },
];

const PROVIDERS = [
  { name: "Ollama", status: "Implemented" },
  { name: "OpenAI", status: "Roadmap" },
  { name: "Anthropic", status: "Roadmap" },
  { name: "Gemini", status: "Roadmap" },
  { name: "Groq", status: "Roadmap" },
  { name: "OpenRouter", status: "Roadmap" },
  { name: "LM Studio", status: "Roadmap" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* Nav */}
      <header className="border-b border-[var(--border)]">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)]">
              <Boxes className="h-4 w-4" />
            </div>
            <span className="font-semibold">ModelBridge</span>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <a href="#features" className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              Features
            </a>
            <a href="#api" className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              API
            </a>
            <Link
              href="/login"
              className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-md bg-[var(--primary)] px-3 py-1.5 text-[var(--primary-foreground)] hover:opacity-90"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 py-24 text-center">
        <h1 className="mx-auto max-w-3xl text-5xl font-bold tracking-tight sm:text-6xl">
          One API. Every AI model.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-[var(--muted-foreground)]">
          ModelBridge is an open-source, self-hostable AI gateway and intelligent
          model router for cloud and local AI models.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/register"
            className="inline-flex items-center gap-2 rounded-md bg-[var(--primary)] px-6 py-3 text-[var(--primary-foreground)] hover:opacity-90"
          >
            Get Started <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="#api"
            className="inline-flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--secondary)] px-6 py-3 text-[var(--secondary-foreground)] hover:bg-[var(--muted)]"
          >
            View Documentation
          </a>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-center text-3xl font-bold">Features</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-[var(--muted-foreground)]">
          A solid foundation for unifying every AI provider behind one API.
        </p>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <Card key={f.title}>
                <CardHeader>
                  <Icon className="h-6 w-6 text-[var(--muted-foreground)]" />
                  <CardTitle className="text-base">{f.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{f.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section className="border-y border-[var(--border)] bg-[var(--card)]">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-center text-3xl font-bold">How it works</h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            {[
              {
                icon: Plug,
                title: "1. Connect providers",
                description: "Add an Ollama instance (or another provider) and point it at your models.",
              },
              {
                icon: GitFork,
                title: "2. One gateway",
                description: "ModelBridge routes your requests to the right provider and returns OpenAI-compatible responses.",
              },
              {
                icon: Boxes,
                title: "3. Use any SDK",
                description: "Call a single /v1/chat/completions endpoint with your existing OpenAI tooling.",
              },
            ].map((s) => {
              const Icon = s.icon;
              return (
                <Card key={s.title}>
                  <CardHeader>
                    <Icon className="h-6 w-6 text-[var(--muted-foreground)]" />
                    <CardTitle className="text-base">{s.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>{s.description}</CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Supported providers */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-center text-3xl font-bold">Supported providers</h2>
        <div className="mx-auto mt-10 flex max-w-3xl flex-wrap items-center justify-center gap-3">
          {PROVIDERS.map((p) => (
            <div
              key={p.name}
              className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-2"
            >
              <Cpu className="h-4 w-4 text-[var(--muted-foreground)]" />
              <span className="text-sm font-medium">{p.name}</span>
              <Badge variant={p.status === "Implemented" ? "success" : "secondary"}>
                {p.status}
              </Badge>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-sm text-[var(--muted-foreground)]">
          Ollama ships today. Additional providers are on the roadmap.
        </p>
      </section>

      {/* API */}
      <section id="api" className="border-t border-[var(--border)] bg-[var(--card)]">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-center text-3xl font-bold">OpenAI-compatible API</h2>
          <p className="mx-auto mt-3 max-w-2xl text-center text-[var(--muted-foreground)]">
            Drop it into your existing code. No new SDK to learn.
          </p>
          <pre className="mx-auto mt-8 max-w-2xl overflow-x-auto rounded-lg bg-black p-6 text-sm text-green-300">
{`from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="YOUR_MODELBRIDGE_API_KEY",
)

response = client.chat.completions.create(
    model="llama3",
    messages=[{"role": "user", "content": "Hello from ModelBridge!"}],
)

print(response.choices[0].message.content)`}
          </pre>
        </div>
      </section>

      {/* Self-hosted */}
      <section className="mx-auto max-w-6xl px-6 py-16 text-center">
        <Lock className="mx-auto h-8 w-8 text-[var(--muted-foreground)]" />
        <h2 className="mt-4 text-3xl font-bold">Self-hosted architecture</h2>
        <p className="mx-auto mt-3 max-w-2xl text-[var(--muted-foreground)]">
          Run the entire stack — web dashboard, API gateway, PostgreSQL, and Redis —
          with a single Docker command. Your data stays yours.
        </p>
        <Link
          href="/register"
          className="mt-8 inline-flex items-center gap-2 rounded-md bg-[var(--primary)] px-6 py-3 text-[var(--primary-foreground)] hover:opacity-90"
        >
          Get Started <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      <footer className="border-t border-[var(--border)] py-8 text-center text-sm text-[var(--muted-foreground)]">
        ModelBridge — One API. Every AI model. Open source.
      </footer>
    </div>
  );
}
