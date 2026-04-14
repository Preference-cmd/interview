"use client";

import React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export function StoreDetailSkeleton() {
  return (
    <div className="min-h-screen bg-parchment animate-in fade-in duration-500">
      {/* Header Skeleton */}
      <header className="border-b border-anthropic-near-black/5 bg-parchment/80 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-[1200px] mx-auto px-8 min-h-16 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-col gap-3">
            <Skeleton className="h-4 w-32 bg-warm-sand" />
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-64 bg-warm-sand" />
              <Skeleton className="h-6 w-16 bg-warm-sand" />
            </div>
            <Skeleton className="h-3 w-48 bg-warm-sand" />
          </div>
          <div className="flex items-center gap-3">
            <Skeleton className="h-9 w-32 rounded-generously-rounded bg-warm-sand" />
            <Skeleton className="h-9 w-28 rounded-generously-rounded bg-warm-sand" />
          </div>
        </div>
      </header>

      <main className="max-w-[1200px] mx-auto p-8">
        <div className="flex flex-col lg:flex-row gap-8 items-start">
          
          {/* Left Panel Skeleton */}
          <aside className="w-full lg:w-[320px] space-y-6">
            <Card className="bg-ivory border-border-cream rounded-very-rounded shadow-whisper overflow-hidden">
              <CardContent className="p-6 space-y-6">
                <div className="space-y-4">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="flex justify-between items-center">
                      <Skeleton className="h-3 w-20 bg-warm-sand/50" />
                      <Skeleton className="h-3 w-24 bg-warm-sand/50" />
                    </div>
                  ))}
                </div>
                <SeparatorSkeleton />
                <div className="space-y-3">
                  <Skeleton className="h-3 w-16 bg-warm-sand/50" />
                  <div className="flex flex-wrap gap-2">
                    <Skeleton className="h-5 w-16 rounded-full bg-warm-sand/50" />
                    <Skeleton className="h-5 w-20 rounded-full bg-warm-sand/50" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-ivory border-border-cream rounded-very-rounded shadow-whisper overflow-hidden">
              <CardHeader>
                <Skeleton className="h-5 w-24 bg-warm-sand/50" />
              </CardHeader>
              <CardContent className="h-[180px]">
                <Skeleton className="h-full w-full bg-warm-sand/30" />
              </CardContent>
            </Card>
          </aside>

          {/* Right Panel Skeleton */}
          <section className="flex-1 w-full space-y-8">
            {/* Workflow Steps Skeleton */}
            <div className="flex justify-between items-center px-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex flex-col items-center gap-2">
                  <Skeleton className="size-8 rounded-full bg-warm-sand" />
                  <Skeleton className="h-2 w-12 bg-warm-sand/50" />
                </div>
              ))}
            </div>

            {/* Tabs Skeleton */}
            <div className="space-y-6">
              <div className="flex gap-8 border-b border-anthropic-near-black/5 pb-2">
                <Skeleton className="h-4 w-20 bg-warm-sand" />
                <Skeleton className="h-4 w-24 bg-warm-sand" />
                <Skeleton className="h-4 w-16 bg-warm-sand" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Skeleton className="h-[300px] rounded-very-rounded bg-warm-sand/20" />
                <Skeleton className="h-[300px] rounded-very-rounded bg-warm-sand/20" />
              </div>

              <Card className="border-anthropic-near-black/5 rounded-very-rounded overflow-hidden">
                <CardHeader className="space-y-2">
                  <Skeleton className="h-6 w-48 bg-warm-sand" />
                  <Skeleton className="h-3 w-64 bg-warm-sand/50" />
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-12 w-full bg-warm-sand/30" />
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

function SeparatorSkeleton() {
  return <div className="h-px w-full bg-border-cream my-2" />;
}
