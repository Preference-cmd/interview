"use client";

import React, { useState } from "react";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AgentRun, AGENT_COLORS } from "@/lib/types";
import { cn, getRelativeTime } from "@/lib/utils";
import { Eye, Clock, Terminal } from "lucide-react";

interface AgentRunsTableProps {
  runs: AgentRun[];
  className?: string;
}

export function AgentRunsTable({ runs, className }: AgentRunsTableProps) {
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);

  const getAgentLabel = (type: string) => {
    switch (type) {
      case "analyzer": return "Diagnosis";
      case "web_operator": return "Backend";
      case "mobile_operator": return "Mobile";
      case "reporter": return "Report";
      default: return type.charAt(0).toUpperCase() + type.slice(1);
    }
  };

  const getStatusColorClass = (status: string) => {
    switch (status.toLowerCase()) {
      case "success": return "text-olive-gray";
      case "failed": return "text-error-crimson";
      case "running": return "text-terracotta";
      default: return "text-stone-gray";
    }
  };

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-stone-gray/50 italic font-serif bg-anthropic-near-black/[0.01] rounded-comfortably-rounded border border-dashed border-border-warm">
        <Terminal className="size-8 mb-2 opacity-20" aria-hidden="true" />
        <p>No agent runs recorded for this store</p>
      </div>
    );
  }

  return (
    <div className={cn("w-full overflow-hidden", className)}>
      <div className="rounded-comfortably-rounded border border-border-warm bg-ivory shadow-whisper overflow-hidden">
        <Table>
          <TableHeader className="bg-parchment/50">
            <TableRow className="hover:bg-transparent border-border-warm">
              <TableHead className="w-[120px] font-mono text-[10px] uppercase tracking-wider text-stone-gray">Type</TableHead>
              <TableHead className="w-[100px] font-mono text-[10px] uppercase tracking-wider text-stone-gray">Status</TableHead>
              <TableHead className="font-mono text-[10px] uppercase tracking-wider text-stone-gray hidden md:table-cell">Duration</TableHead>
              <TableHead className="font-mono text-[10px] uppercase tracking-wider text-stone-gray">Timestamp</TableHead>
              <TableHead className="text-right font-mono text-[10px] uppercase tracking-wider text-stone-gray">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id} className="border-border-warm hover:bg-parchment/30 transition-colors">
                <TableCell>
                  <Badge 
                    variant="secondary" 
                    className="text-[10px] uppercase tracking-wider font-mono py-0 h-5 bg-warm-sand border-border-warm text-stone-gray whitespace-nowrap"
                    style={{ 
                      borderLeft: `3px solid ${AGENT_COLORS[run.agent_type] || '#87867f'}` 
                    }}
                  >
                    {getAgentLabel(run.agent_type)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span className={cn(
                    "text-xs font-medium uppercase tracking-wide",
                    getStatusColorClass(run.status)
                  )}>
                    {run.status}
                  </span>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <div className="flex items-center gap-1.5 text-xs text-olive-gray font-mono">
                    <Clock className="size-3 opacity-40" />
                    {run.duration_ms}ms
                  </div>
                </TableCell>
                <TableCell>
                  <span 
                    className="text-xs text-stone-gray font-mono cursor-help"
                    title={new Date(run.created_at).toLocaleString()}
                  >
                    {getRelativeTime(run.created_at)}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-7 px-2 text-[10px] text-olive-gray hover:text-anthropic-near-black hover:bg-warm-sand gap-1.5 rounded-sharp"
                        onClick={() => setSelectedRun(run)}
                      >
                        <Eye className="size-3" />
                        View Output
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[600px] bg-ivory border-border-warm shadow-2xl rounded-very-rounded">
                      <DialogHeader>
                        <DialogTitle className="font-serif text-xl flex items-center gap-2">
                          <Terminal className="size-5 text-terracotta" />
                          Agent Output Details
                        </DialogTitle>
                      </DialogHeader>
                      <div className="mt-4 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-3 bg-parchment rounded-subtly-rounded border border-border-warm flex flex-col gap-1">
                            <span className="text-[10px] uppercase tracking-widest text-stone-gray font-mono">Agent Type</span>
                            <span className="text-sm font-medium text-olive-gray">{getAgentLabel(run.agent_type)}</span>
                          </div>
                          <div className="p-3 bg-parchment rounded-subtly-rounded border border-border-warm flex flex-col gap-1">
                            <span className="text-[10px] uppercase tracking-widest text-stone-gray font-mono">Execution Status</span>
                            <span className={cn("text-sm font-medium uppercase tracking-wide", getStatusColorClass(run.status))}>
                              {run.status}
                            </span>
                          </div>
                        </div>
                        
                        <div className="relative group">
                          <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Badge variant="outline" className="bg-ivory/80 backdrop-blur-sm text-[10px] font-mono border-border-warm">JSON</Badge>
                          </div>
                          <ScrollArea className="h-[400px] w-full rounded-comfortably-rounded border border-border-warm bg-parchment">
                            <pre className="p-6 text-[11px] font-mono text-olive-gray leading-relaxed selection:bg-terracotta/10">
                              {JSON.stringify(run.output_data, null, 2)}
                            </pre>
                          </ScrollArea>
                        </div>

                        {run.error_msg && (
                          <div className="p-4 bg-error-crimson/5 border border-error-crimson/20 rounded-comfortably-rounded">
                            <h4 className="text-[10px] uppercase tracking-widest text-error-crimson font-mono mb-2">Error Message</h4>
                            <p className="text-xs text-error-crimson/90 italic font-serif">{run.error_msg}</p>
                          </div>
                        )}
                      </div>
                    </DialogContent>
                  </Dialog>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
