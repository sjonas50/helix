"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/lib/auth/useAuth";

export default function LoginPage() {
  const [orgSlug, setOrgSlug] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const login = useAuth((s) => s.login);
  const router = useRouter();

  function handleSSO() {
    alert(`SSO redirect for org "${orgSlug}" — not configured in development.`);
  }

  async function handleDevLogin() {
    setLoading(true);
    setError(null);
    try {
      // Fetch a real signed JWT from the backend dev endpoint
      const res = await fetch("http://localhost:8000/api/v1/dev/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        throw new Error(`Failed to get dev token: ${res.status}`);
      }
      const data = await res.json();
      login(data.token);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">Helix</CardTitle>
          <CardDescription>
            Enterprise AI Agent Platform
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="org-slug">Organization</Label>
            <Input
              id="org-slug"
              placeholder="your-org-slug"
              value={orgSlug}
              onChange={(e) => setOrgSlug(e.target.value)}
            />
          </div>
          <Button
            variant="default"
            className="w-full"
            onClick={handleSSO}
            disabled={!orgSlug.trim()}
          >
            Sign In with SSO
          </Button>
          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">
                Development
              </span>
            </div>
          </div>
          <Button variant="outline" className="w-full" onClick={handleDevLogin} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Dev Login
          </Button>
          {error && (
            <p className="text-sm text-red-600 text-center">{error}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
