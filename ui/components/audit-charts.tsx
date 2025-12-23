"use client"

import { useEffect, useState, useMemo } from "react"
import { Card } from "@/components/ui/card"
import { Loader2, BarChart3, PieChart } from "lucide-react"
import { getAuditStats, AuditStats } from "@/lib/api"
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    PieChart as RePieChart,
    Pie,
    Legend,
} from "recharts"
import { format, subDays, parseISO, startOfDay } from "date-fns"
import { tr } from "date-fns/locale"

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"]

export function AuditCharts({ token }: { token: string }) {
    const [stats, setStats] = useState<AuditStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        getAuditStats(token)
            .then(setStats)
            .catch((err) =>
                setError(err instanceof Error ? err.message : "İstatistikler yüklenemedi")
            )
            .finally(() => setLoading(false))
    }, [token])

    // Process daily stats to ensure last 7 days are shown even if count is 0
    const processedDailyStats = useMemo(() => {
        if (!stats?.daily_activity) return []

        const today = startOfDay(new Date())
        const last7Days = Array.from({ length: 7 }, (_, i) => {
            const d = subDays(today, 6 - i)
            return {
                date: format(d, "yyyy-MM-dd"),
                displayDate: format(d, "d MMM", { locale: tr }),
                count: 0,
            }
        })

        // Merge API data
        // API returns "YYYY-MM-DD"
        stats.daily_activity.forEach((item) => {
            const found = last7Days.find((d) => d.date === item.date)
            if (found) {
                found.count = item.count
            }
        })

        return last7Days
    }, [stats])

    if (loading)
        return (
            <Card className="p-6 flex justify-center items-center h-48">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </Card>
        )

    if (error)
        return (
            <Card className="p-6 text-destructive border-destructive/20 bg-destructive/5">
                İstatistik hatası: {error}
            </Card>
        )

    if (!stats) return null

    return (
        <div className="grid gap-6 md:grid-cols-2 mb-6">
            {/* Daily Activity */}
            <Card className="p-6">
                <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold">Günlük Aktivite (Son 7 Gün)</h3>
                </div>
                <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={processedDailyStats}>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-muted/20" vertical={false} />
                            <XAxis
                                dataKey="displayDate"
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                interval={0}
                            />
                            <YAxis
                                stroke="#888888"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                                allowDecimals={false}
                            />
                            <Tooltip
                                cursor={{ fill: 'hsl(var(--muted)/0.4)' }}
                                contentStyle={{
                                    borderRadius: "8px",
                                    border: "1px solid hsl(var(--border))",
                                    backgroundColor: "hsl(var(--popover))",
                                    color: "hsl(var(--popover-foreground))",
                                    boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
                                }}
                                itemStyle={{ color: "hsl(var(--foreground))" }}
                                labelStyle={{ color: "hsl(var(--foreground))", fontWeight: "bold" }}
                                formatter={(value: number) => [value, "İşlem Sayısı"]}
                            />
                            <Bar
                                dataKey="count"
                                fill="#60a5fa"
                                radius={[4, 4, 0, 0]}
                                maxBarSize={50}
                                name="İşlem Sayısı"
                            />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </Card>

            {/* Action Distribution */}
            <Card className="p-6">
                <div className="flex items-center gap-2 mb-4">
                    <PieChart className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold">Aksiyon Dağılımı</h3>
                </div>
                {/* Increased height to avoid overlap */}
                <div className="h-[350px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <RePieChart>
                            <Pie
                                data={stats.action_distribution}
                                cx="35%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={85}
                                paddingAngle={2}
                                dataKey="count"
                                stroke="hsl(var(--card))"
                                strokeWidth={2}
                            >
                                {stats.action_distribution.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={COLORS[index % COLORS.length]}
                                        name={entry.action}
                                    />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{
                                    borderRadius: "8px",
                                    border: "1px solid hsl(var(--border))",
                                    backgroundColor: "hsl(var(--popover))",
                                    color: "hsl(var(--popover-foreground))",
                                    boxShadow: "0 4px 12px rgba(0,0,0,0.2)"
                                }}
                                itemStyle={{ color: "hsl(var(--foreground))" }}
                                formatter={(value: number, name: string) => {
                                    // Tooltip formatter for readable names
                                    const formatted = name
                                        .replace(/^(ADMIN_|QUIZ_|USER_)/, "")
                                        .replace(/_/g, " ")
                                        .toLowerCase()
                                        .replace(/\b\w/g, (c: string) => c.toUpperCase())
                                    return [value, formatted]
                                }}
                            />
                            <Legend
                                layout="vertical"
                                verticalAlign="middle"
                                align="right"
                                formatter={(value) => {
                                    // Format: "ADMIN_GENERATE_QUESTION" -> "Generate Question"
                                    const formatted = value
                                        .replace(/^(ADMIN_|QUIZ_|USER_)/, "") // Remove common prefixes
                                        .replace(/_/g, " ")
                                        .toLowerCase()
                                        .replace(/\b\w/g, (c: string) => c.toUpperCase())

                                    return (
                                        <span title={value} style={{ color: "hsl(var(--foreground))", fontSize: "11px", display: "inline-block", maxWidth: "150px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                            {formatted}
                                        </span>
                                    )
                                }}
                            />
                        </RePieChart>
                    </ResponsiveContainer>
                </div>
            </Card>
        </div>
    )
}
