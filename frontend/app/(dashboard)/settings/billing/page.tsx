"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useUsageStats } from "@/lib/api/settings";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

// Hardcoded sample data for development visualization
const modelUsageData = [
  { model: "GPT-4o", input: 1_240_000, output: 620_000 },
  { model: "Claude 3.5", input: 890_000, output: 445_000 },
  { model: "GPT-4o-mini", input: 2_100_000, output: 1_050_000 },
  { model: "Claude Haiku", input: 3_400_000, output: 1_700_000 },
];

const dailyCostData = [
  { date: "Mar 24", cost: 12.5 },
  { date: "Mar 25", cost: 18.3 },
  { date: "Mar 26", cost: 15.1 },
  { date: "Mar 27", cost: 22.7 },
  { date: "Mar 28", cost: 19.4 },
  { date: "Mar 29", cost: 25.8 },
  { date: "Mar 30", cost: 21.2 },
];

const summaryCards = [
  { title: "Total Tokens", value: "11.4M" },
  { title: "Total Cost", value: "$134.80" },
  { title: "Most Expensive Workflow", value: "Customer Onboarding" },
];

export default function BillingPage() {
  // Hook available for real data when backend is connected
  useUsageStats();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Billing & Usage</h1>
        <p className="text-muted-foreground">
          Monitor token consumption and costs across models and workflows.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        {summaryCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Token usage by model */}
      <Card>
        <CardHeader>
          <CardTitle>Token Usage by Model</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72" data-testid="bar-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelUsageData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" fontSize={12} />
                <YAxis
                  fontSize={12}
                  tickFormatter={(v: number) =>
                    v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : `${(v / 1_000).toFixed(0)}K`
                  }
                />
                <Tooltip
                  formatter={(value) => String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
                />
                <Bar
                  dataKey="input"
                  name="Input Tokens"
                  fill="#3b82f6"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="output"
                  name="Output Tokens"
                  fill="#8b5cf6"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Daily cost trend */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Cost Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72" data-testid="line-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyCostData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" fontSize={12} />
                <YAxis
                  fontSize={12}
                  tickFormatter={(v: number) => `$${v}`}
                />
                <Tooltip
                  formatter={(value) => [`$${Number(value).toFixed(2)}`, "Cost"]}
                />
                <Line
                  type="monotone"
                  dataKey="cost"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
