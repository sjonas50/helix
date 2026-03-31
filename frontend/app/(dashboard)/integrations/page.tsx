"use client";

import { useMemo } from "react";
import { useProviders } from "@/lib/api/integrations";
import { useIntegrations } from "@/lib/api/integrations";
import { useConnectIntegration } from "@/lib/api/integrations";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Plug, PlugZap } from "lucide-react";

export default function IntegrationsPage() {
  const { data: providers, isLoading: loadingProviders } = useProviders();
  const { data: integrations, isLoading: loadingIntegrations } =
    useIntegrations();
  const connectMutation = useConnectIntegration();

  const connectedSet = useMemo(() => {
    const set = new Set<string>();
    integrations?.forEach((i) => {
      if (i.enabled) set.add(i.provider);
    });
    return set;
  }, [integrations]);

  const isLoading = loadingProviders || loadingIntegrations;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground">
            Connect external tools and services to your workflows.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Integrations</h1>
        <p className="text-muted-foreground">
          Connect external tools and services to your workflows.
        </p>
      </div>

      {(!providers || providers.length === 0) && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Plug className="mb-4 size-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No integration providers available yet.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {providers?.map((provider) => {
          const isConnected = connectedSet.has(provider);
          return (
            <Card key={provider}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-2">
                  <PlugZap className="size-5 text-muted-foreground" />
                  <CardTitle className="text-base font-semibold capitalize">
                    {provider}
                  </CardTitle>
                </div>
                <Badge
                  variant="outline"
                  className={
                    isConnected
                      ? "bg-green-500/10 text-green-700 dark:text-green-400"
                      : "bg-zinc-500/10 text-zinc-500"
                  }
                >
                  {isConnected ? "Connected" : "Not Connected"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  {isConnected
                    ? "Integration active and available to agents."
                    : "Connect to enable this provider in your workflows."}
                </p>
                <Button
                  size="sm"
                  variant={isConnected ? "outline" : "default"}
                  disabled={connectMutation.isPending}
                  onClick={() => {
                    if (!isConnected) {
                      connectMutation.mutate({ provider });
                    }
                  }}
                >
                  {isConnected ? "Manage" : "Connect"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
