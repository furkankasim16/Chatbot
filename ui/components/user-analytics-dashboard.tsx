
"use client"

import { Card } from "@/components/ui/card"
import { UserStats } from "@/lib/api"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { Lightbulb, TrendingUp, BookOpen, AlertCircle } from "lucide-react"

interface UserAnalyticsDashboardProps {
    stats: UserStats
}

export function UserAnalyticsDashboard({ stats }: UserAnalyticsDashboardProps) {
    if (!stats) return null

    // Transform topic_stats for Recharts
    const topicData = Object.entries(stats.topic_stats || {}).map(([topic, data]) => ({
        name: topic,
        correct: data.correct,
        total: data.total,
        score: data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0
    })).sort((a, b) => b.score - a.score)

    // Colors for bars based on score
    const getBarColor = (score: number) => {
        if (score >= 80) return "#22c55e" // green-500
        if (score >= 60) return "#eab308" // yellow-500
        return "#ef4444" // red-500
    }

    return (
        <div className="space-y-6">
            {/* 🧠 Recommendation Banner */}
            {stats.recommended_study_topics && stats.recommended_study_topics.length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-lg p-4 flex items-start gap-3">
                    <Lightbulb className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-1 shrink-0" />
                    <div>
                        <h4 className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
                            Yapay Zeka Öneriyor: Çalışılması Gereken Konular
                        </h4>
                        <p className="text-sm text-amber-800 dark:text-amber-300 mb-2">
                            Aşağıdaki konulardaki başarı oranınız düşük görünüyor. Bu konulara odaklanarak gelişiminizi hızlandırabilirsiniz:
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {stats.recommended_study_topics.map((topic, i) => (
                                <span key={i} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-800">
                                    <BookOpen className="w-3 h-3 mr-1" />
                                    {topic}
                                </span>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <div className="grid gap-6 md:grid-cols-2">
                {/* 📊 Topic Performance Chart */}
                <Card className="p-6 md:col-span-2">
                    <div className="flex items-center gap-2 mb-6">
                        <TrendingUp className="w-5 h-5 text-primary" />
                        <h3 className="font-semibold text-lg">Konu Bazlı Başarı Analizi</h3>
                    </div>

                    <div className="h-[300px] w-full">
                        {topicData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    data={topicData}
                                    layout="vertical"
                                    margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                                    <XAxis type="number" domain={[0, 100]} hide />
                                    <YAxis
                                        type="category"
                                        dataKey="name"
                                        width={120}
                                        tick={{ fontSize: 12 }}
                                    />
                                    <Tooltip
                                        formatter={(value: number) => [`%${value}`, 'Başarı']}
                                        labelStyle={{ color: 'black' }}
                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                    />
                                    <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={20}>
                                        {topicData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={getBarColor(entry.score)} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground bg-muted/20 rounded-lg">
                                <AlertCircle className="w-8 h-8 mb-2 opacity-50" />
                                <p>Henüz yeterli veri yok.</p>
                            </div>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    )
}
