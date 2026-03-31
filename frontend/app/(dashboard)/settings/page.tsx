"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Building2, Gauge, Users, CreditCard } from "lucide-react";

const sections = [
  {
    title: "General",
    description: "Organization name, plan, and core settings.",
    href: "/settings",
    icon: Building2,
  },
  {
    title: "Autonomy",
    description: "Configure per-workflow autonomy levels for agents.",
    href: "/settings/autonomy",
    icon: Gauge,
  },
  {
    title: "Members",
    description: "Manage team members and role-based access control.",
    href: "/settings/members",
    icon: Users,
  },
  {
    title: "Billing",
    description: "Token usage, cost tracking, and plan details.",
    href: "/settings/billing",
    icon: CreditCard,
  },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your organization configuration, team, and billing.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {sections.map((section) => (
          <Link key={section.title} href={section.href}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                <section.icon className="size-5 text-muted-foreground" />
                <CardTitle className="text-base">{section.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {section.description}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
