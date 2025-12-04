// app/types/llm.ts
export interface LlmStatsSummary {
  model_name: string;
  total_calls: number;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  avg_input_tokens: number | null;
  avg_output_tokens: number | null;
}
