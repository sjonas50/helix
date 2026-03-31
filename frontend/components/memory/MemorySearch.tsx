"use client";

import { useState, useEffect, useMemo } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useMemorySearch } from "@/lib/api/memory";
import { MemoryCard } from "./MemoryCard";
import type { MemoryQuery } from "@/types/api";

export function MemorySearch() {
  const [rawQuery, setRawQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(rawQuery), 300);
    return () => clearTimeout(timer);
  }, [rawQuery]);

  const searchQuery: MemoryQuery | null = useMemo(
    () => (debouncedQuery.trim() ? { query: debouncedQuery.trim() } : null),
    [debouncedQuery]
  );

  const { data: results, isLoading } = useMemorySearch(searchQuery);

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search institutional memory..."
          value={rawQuery}
          onChange={(e) => setRawQuery(e.target.value)}
          className="pl-10"
          data-testid="memory-search-input"
        />
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-lg" />
          ))}
        </div>
      )}

      {!isLoading && results && results.length === 0 && debouncedQuery && (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No memories found. Try a different query.
        </p>
      )}

      {!isLoading && results && results.length > 0 && (
        <div className="space-y-3">
          {results.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} />
          ))}
        </div>
      )}
    </div>
  );
}
