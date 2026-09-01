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
  Check,
  Star,
  Github,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Plug,
    title: "One OpenAI-compatible API",
    description:
      "Use your existing OpenAI SDKs and tools. ModelBridge exposes a single /v1/chat/completions endpoint across all providers.",
    color: "from-blue-500 to-cyan-400",
  },
  {
    icon: Server,
    title: "Cloud & local providers",
    description:
      "Connect cloud AI services and local models running on your own hardware through a unified interface.",
    color: "from-violet-500 to-purple-400",
  },
  {
    icon: Workflow,
    title: "Intelligent routing",
    description:
      "Route each request to the best provider by cost, speed, quality, or privacy. Automatic fallback when a provider is down.",
    color: "from-amber-500 to-orange-400",
  },
  {
    icon: KeyRound,
    title: "API key management",
    description:
      "Issue scoped API keys, rotate and revoke them, and authenticate every request securely.",
    color: "from-emerald-500 to-green-400",
  },
  {
    icon: Lock,
    title: "Self-hosted",
    description:
      "Run ModelBridge entirely on your own infrastructure. Your prompts and keys never leave your control.",
    color: "from-rose-500 to-pink-400",
  },
  {
    icon: Shield,
    title: "Secure by design",
    description:
      "Passwords hashed, provider secrets encrypted, API keys stored as hashes only.",
    color: "from-indigo-500 to-blue-400",
  },
];

const PROVIDERS = [
  { name: "Ollama", status: "Implemented" as const },
  { name: "OpenAI", status: "Roadmap" as const },
  { name: "Anthropic", status: "Roadmap" as const },
  { name: "Gemini", status: "Roadmap" as const },
  { name: "Groq", status: "Roadmap" as const },
  { name: "OpenRouter", status: "Roadmap" as const },
  { name: "LM Studio", status: "Roadmap" as const },
];

const TESTIMONIALS = [
  {
    quote: "Finally one endpoint for all my models. Switched from juggling 4 different APIs.",
    author: "ML Engineer",
    role: "Series A startup",
  },
  {
    quote: "The self-hosted option means we keep our data in-house. Perfect for compliance.",
    author: "Platform Lead",
    role: "Healthcare company",
  },
  {
    quote: "Dropped right into our OpenAI codebase. Zero SDK changes needed.",
    author: "Founding Engineer",
    role: "AI-native SaaS",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* ── Nav ── */}
      <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand-gradient)] shadow-sm">
              <Boxes className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold tracking-tight">ModelBridge</span>
          </div>
          <nav className="flex items-center gap-1 text-sm">
            <a href="#features" className="rounded-md px-3 py-2 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]">
              Features
            </a>
            <a href="#api" className="rounded-md px-3 py-2 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]">
              API
            </a>
            <a href="#providers" className="rounded-md px-3 py-2 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]">
              Providers
            </a>
            <div className="ml-2 flex items-center gap-2">
              <Link href="/login" className="rounded-md px-3 py-2 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)] hover:text-[var(--foreground)]">
                Sign in
              </Link>
              <Link href="/register">
                <Button size="sm">Get Started</Button>
              </Link>
            </div>
          </nav>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative overflow-hidden">
        {/* Background decorations */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-[var(--brand-gradient-soft)] blur-3xl opacity-60" />
          <div className="absolute top-20 right-[10%] h-72 w-72 rounded-full bg-blue-500/5 blur-3xl" />
          <div className="absolute top-40 left-[10%] h-72 w-72 rounded-full bg-violet-500/5 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-6xl px-6 pt-24 pb-32 text-center">
          {/* Badge */}
          <div className="mb-8 inline-flex animate-fade-in items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-1.5 text-sm text-[var(--muted-foreground)] shadow-sm">
            <Star className="h-3.5 w-3.5 text-amber-500" />
            <span>Open source &middot; Self-hosted &middot; Production ready</span>
          </div>

          {/* Headline */}
          <h1 className="mx-auto max-w-4xl text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl animate-slide-up">
            One API.
            <br />
            <span className="text-gradient">Every AI model.</span>
          </h1>

          {/* Subheadline */}
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-[var(--muted-foreground)] animate-slide-up" style={{ animationDelay: "0.1s" }}>
            ModelBridge is an open-source, self-hostable AI gateway and intelligent
            model router. Connect cloud and local AI providers behind a single,
            OpenAI-compatible endpoint.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4 animate-slide-up" style={{ animationDelay: "0.2s" }}>
            <Link href="/register">
              <Button size="xl" variant="gradient" className="animate-pulse-glow">
                Get Started Free <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <a href="#api">
              <Button size="xl" variant="outline">
                View Documentation
              </Button>
            </a>
          </div>

          {/* Code snippet preview */}
          <div className="mx-auto mt-16 max-w-2xl animate-slide-up" style={{ animationDelay: "0.3s" }}>
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-1 shadow-xl">
              <div className="flex items-center gap-2 rounded-t-xl border-b border-[var(--border)] bg-[var(--muted)]/50 px-4 py-2.5">
                <div className="flex gap-1.5">
                  <div className="h-3 w-3 rounded-full bg-red-400" />
                  <div className="h-3 w-3 rounded-full bg-amber-400" />
                  <div className="h-3 w-3 rounded-full bg-green-400" />
                </div>
                <span className="ml-2 text-xs text-[var(--muted-foreground)]">quickstart.py</span>
              </div>
              <pre className="overflow-x-auto rounded-b-xl p-5 text-left text-sm leading-relaxed">
                <code>
                  <span className="text-violet-600 dark:text-violet-400">from</span>{" "}
                  <span className="text-amber-600 dark:text-amber-400">openai</span>{" "}
                  <span className="text-violet-600 dark:text-violet-400">import</span>{" "}
                  <span className="text-cyan-600 dark:text-cyan-400">OpenAI</span>
                  {"\n\n"}
                  <span className="text-cyan-600 dark:text-cyan-400">client</span>{" "}
                  <span className="text-[var(--muted-foreground)]">=</span>{" "}
                  <span className="text-cyan-600 dark:text-cyan-400">OpenAI</span>(
                  {"\n"}
                  {"    "}<span className="text-emerald-600 dark:text-emerald-400">base_url</span>
                  <span className="text-[var(--muted-foreground)]">=</span>
                  <span className="text-amber-600 dark:text-amber-400">&quot;http://localhost:8000/v1&quot;</span>,
                  {"\n"}
                  {"    "}<span className="text-emerald-600 dark:text-emerald-400">api_key</span>
                  <span className="text-[var(--muted-foreground)]">=</span>
                  <span className="text-amber-600 dark:text-amber-400">&quot;YOUR_API_KEY&quot;</span>,
                  {"\n"}{"\n"}
                  <span className="text-cyan-600 dark:text-cyan-400">response</span>{" "}
                  <span className="text-[var(--muted-foreground)]">=</span>{" "}
                  <span className="text-cyan-600 dark:text-cyan-400">client</span>.chat.completions.create(
                  {"\n"}
                  {"    "}<span className="text-emerald-600 dark:text-emerald-400">model</span>
                  <span className="text-[var(--muted-foreground)]">=</span>
                  <span className="text-amber-600 dark:text-amber-400">&quot;llama3&quot;</span>,
                  {"\n"}
                  {"    "}<span className="text-emerald-600 dark:text-emerald-400">messages</span>
                  <span className="text-[var(--muted-foreground)]">=</span>[{`{`}<span className="text-amber-600 dark:text-amber-400">&quot;role&quot;</span>: <span className="text-amber-600 dark:text-amber-400">&quot;user&quot;</span>, <span className="text-amber-600 dark:text-amber-400">&quot;content&quot;</span>: <span className="text-amber-600 dark:text-amber-400">&quot;Hello!&quot;</span>{`}`}],
                  {"\n"}{"\n"}
                  <span className="text-blue-600 dark:text-blue-400">print</span>(response.choices[<span className="text-cyan-600 dark:text-cyan-400">0</span>].message.content)
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="relative border-t border-[var(--border)] bg-[var(--card)]/50">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="text-center">
            <Badge variant="gradient" className="mb-4">Features</Badge>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to unify AI
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-[var(--muted-foreground)]">
              A solid foundation for connecting every AI provider behind one API — with
              intelligent routing, security, and observability built in.
            </p>
          </div>

          <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 stagger-children">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="card-interactive group p-6">
                  <div className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${f.color} shadow-sm transition-transform duration-200 group-hover:scale-110`}>
                    <Icon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="text-base font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted-foreground)]">
                    {f.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="border-t border-[var(--border)]">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="text-center">
            <Badge variant="secondary" className="mb-4">How it works</Badge>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Three steps to unified AI
            </h2>
          </div>

          <div className="relative mt-16">
            {/* Connecting line */}
            <div className="absolute left-0 right-0 top-12 hidden h-px bg-gradient-to-r from-transparent via-[var(--border)] to-transparent lg:block" />

            <div className="grid gap-8 sm:grid-cols-3">
              {[
                {
                  num: "01",
                  icon: Plug,
                  title: "Connect providers",
                  description: "Add an Ollama instance (or another provider) and point it at your models.",
                },
                {
                  num: "02",
                  icon: GitFork,
                  title: "One gateway",
                  description: "ModelBridge routes your requests to the right provider and returns OpenAI-compatible responses.",
                },
                {
                  num: "03",
                  icon: Boxes,
                  title: "Use any SDK",
                  description: "Call a single /v1/chat/completions endpoint with your existing OpenAI tooling.",
                },
              ].map((s) => {
                const Icon = s.icon;
                return (
                  <div key={s.title} className="relative text-center">
                    <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-md">
                      <div className="text-center">
                        <span className="text-xs font-bold text-[var(--primary)]">{s.num}</span>
                        <Icon className="mx-auto mt-1 h-6 w-6 text-[var(--muted-foreground)]" />
                      </div>
                    </div>
                    <h3 className="text-lg font-semibold">{s.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--muted-foreground)]">
                      {s.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ── Supported Providers ── */}
      <section id="providers" className="border-t border-[var(--border)] bg-[var(--card)]/50">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="text-center">
            <Badge variant="secondary" className="mb-4">Providers</Badge>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Connect to any AI provider
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-[var(--muted-foreground)]">
              Start with Ollama today. OpenAI, Anthropic, and more providers are on the roadmap.
            </p>
          </div>

          <div className="mx-auto mt-12 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {PROVIDERS.map((p) => (
              <div
                key={p.name}
                className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 shadow-sm transition-all duration-200 hover:border-[var(--primary)]/40 hover:shadow-md"
              >
                <Cpu className="h-4 w-4 shrink-0 text-[var(--muted-foreground)]" />
                <div className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{p.name}</span>
                </div>
                <Badge variant={p.status === "Implemented" ? "success" : "secondary"} className="shrink-0">
                  {p.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Testimonials ── */}
      <section className="border-t border-[var(--border)]">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <div className="text-center">
            <Badge variant="secondary" className="mb-4">Testimonials</Badge>
            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Trusted by builders
            </h2>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            {TESTIMONIALS.map((t, i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-sm">
                <div className="mb-4 flex gap-1">
                  {[...Array(5)].map((_, j) => (
                    <Star key={j} className="h-4 w-4 fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <p className="text-sm leading-relaxed text-[var(--foreground)]">&ldquo;{t.quote}&rdquo;</p>
                <div className="mt-4 border-t border-[var(--border)] pt-4">
                  <p className="text-sm font-medium">{t.author}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Self-hosted CTA ── */}
      <section className="border-t border-[var(--border)]">
        <div className="mx-auto max-w-6xl px-6 py-24 text-center">
          <div className="mx-auto max-w-2xl">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--brand-gradient)] shadow-lg">
              <Lock className="h-7 w-7 text-white" />
            </div>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Self-hosted. Always.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-[var(--muted-foreground)] leading-relaxed">
              Run the entire stack — web dashboard, API gateway, PostgreSQL, and Redis —
              with a single Docker command. Your data stays yours, always.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              {["Zero data leakage", "No vendor lock-in", "Full control"].map((perk) => (
                <div key={perk} className="flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm font-medium shadow-sm">
                  <Check className="h-3.5 w-3.5 text-emerald-500" />
                  {perk}
                </div>
              ))}
            </div>
            <Link href="/register" className="mt-8 inline-block">
              <Button size="xl" variant="gradient">
                Get Started <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-[var(--border)] bg-[var(--card)]/50">
        <div className="mx-auto max-w-6xl px-6 py-12">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="flex items-center gap-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--brand-gradient)]">
                <Boxes className="h-3.5 w-3.5 text-white" />
              </div>
              <span className="font-semibold">ModelBridge</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-[var(--muted-foreground)]">
              <a href="#features" className="hover:text-[var(--foreground)] transition-colors">Features</a>
              <a href="#api" className="hover:text-[var(--foreground)] transition-colors">API</a>
              <a href="#providers" className="hover:text-[var(--foreground)] transition-colors">Providers</a>
              <a href="#" className="hover:text-[var(--foreground)] transition-colors flex items-center gap-1.5">
                <Github className="h-4 w-4" /> GitHub
              </a>
            </div>
            <p className="text-xs text-[var(--muted-foreground)]">
              &copy; {new Date().getFullYear()} ModelBridge. Open source.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
