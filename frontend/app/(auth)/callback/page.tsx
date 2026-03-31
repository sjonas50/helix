"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth/useAuth";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const login = useAuth((s) => s.login);
  const router = useRouter();

  const token = searchParams.get("token");

  useEffect(() => {
    if (token) {
      login(token);
      router.replace("/");
    } else {
      router.replace("/login");
    }
  }, [token, login, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">
        {token ? "Authenticating..." : "Redirecting to login..."}
      </p>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
