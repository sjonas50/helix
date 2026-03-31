"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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

function createMockJWT(): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      sub: "usr_dev_001",
      org_id: "org_dev_001",
      email: "dev@helix.local",
      display_name: "Dev User",
      roles: ["admin", "operator"],
      token_type: "user",
      exp: Math.floor(Date.now() / 1000) + 86400,
      iat: Math.floor(Date.now() / 1000),
    })
  );
  const signature = btoa("dev-signature");
  return `${header}.${payload}.${signature}`;
}

export default function LoginPage() {
  const [orgSlug, setOrgSlug] = useState("");
  const login = useAuth((s) => s.login);
  const router = useRouter();

  function handleSSO() {
    // In production: redirect to WorkOS AuthKit with org slug
    // window.location.href = `/api/auth/sso?org=${orgSlug}`;
    alert(`SSO redirect for org "${orgSlug}" — not configured in development.`);
  }

  function handleDevLogin() {
    const token = createMockJWT();
    login(token);
    router.push("/");
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
          <Button variant="outline" className="w-full" onClick={handleDevLogin}>
            Dev Login
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
