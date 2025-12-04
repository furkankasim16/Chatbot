"use client";

import { useEffect, useState } from "react";
import type { LlmStatsSummary } from "@/app/types/llm";


import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table } from "@/components/ui/table"; // kendi table component’ine göre uyarlarsın
import { Loader2 } from "lucide-react";
import { fetchLlmStatsSummary } from "@/lib/api";

export function AdminLlmStats() {
  const [data, setData] = useState<LlmStatsSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const stats = await fetchLlmStatsSummary();
        setData(stats);
      } catch (err: any) {
        setError(err.message ?? "LLM stats yüklenirken hata oluştu");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>LLM Performans Özeti</CardTitle>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Veriler yükleniyor...</span>
          </div>
        )}

        {error && (
          <div className="text-sm text-red-500">
            {error}
          </div>
        )}

        {!loading && !error && data && data.length === 0 && (
          <div className="text-sm text-muted-foreground">
            Henüz kayıtlı LLM çağrısı yok.
          </div>
        )}

        {!loading && !error && data && data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2">Model</th>
                  <th className="text-right py-2 px-2">Çağrı Sayısı</th>
                  <th className="text-right py-2 px-2">Ort. Latency (ms)</th>
                  <th className="text-right py-2 px-2">Min (ms)</th>
                  <th className="text-right py-2 px-2">Max (ms)</th>
                  <th className="text-right py-2 px-2">Ort. Input Tokens</th>
                  <th className="text-right py-2 px-2">Ort. Output Tokens</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.model_name} className="border-b last:border-0">
                    <td className="py-2 px-2 font-mono">{row.model_name}</td>
                    <td className="py-2 px-2 text-right">{row.total_calls}</td>
                    <td className="py-2 px-2 text-right">
                      {row.avg_latency_ms?.toFixed(1) ?? "-"}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {row.min_latency_ms ?? "-"}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {row.max_latency_ms ?? "-"}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {row.avg_input_tokens?.toFixed(1) ?? "-"}
                    </td>
                    <td className="py-2 px-2 text-right">
                      {row.avg_output_tokens?.toFixed(1) ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}