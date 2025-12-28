
import { useEffect, useState } from "react"
import { getLeaderboard, LeaderboardEntry } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Trophy, Medal, Crown } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

interface LeaderboardScreenProps {
    onBack: () => void
}

export function LeaderboardScreen({ onBack }: LeaderboardScreenProps) {
    const [entries, setEntries] = useState<LeaderboardEntry[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getLeaderboard()
            .then(setEntries)
            .catch((err) => console.error(err))
            .finally(() => setLoading(false))
    }, [])

    const getRankIcon = (index: number) => {
        if (index === 0) return <Crown className="w-6 h-6 text-yellow-500" />
        if (index === 1) return <Medal className="w-6 h-6 text-gray-400" />
        if (index === 2) return <Medal className="w-6 h-6 text-amber-700" />
        return <span className="text-xl font-bold text-muted-foreground w-6 text-center">{index + 1}</span>
    }

    const getTitle = (lvl: number) => {
        if (lvl >= 20) return "🔮 Kâhin"
        if (lvl >= 10) return "🧠 Bilgin"
        if (lvl >= 5) return "🎓 Mezun"
        if (lvl >= 3) return "🤓 Meraklı"
        return "🐣 Çırak"
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button onClick={onBack} variant="outline" size="icon">
                    <ArrowLeft className="w-4 h-4" />
                </Button>
                <h2 className="text-3xl font-bold tracking-tight">Liderlik Tablosu</h2>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Trophy className="w-6 h-6 text-primary" />
                        En İyi Öğrenciler
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <div className="text-center py-8">Yükleniyor...</div>
                    ) : (
                        <ScrollArea className="h-[400px]">
                            <div className="space-y-2">
                                {entries.map((entry, index) => (
                                    <div key={entry.username} className="flex items-center justify-between p-4 rounded-lg bg-card border hover:bg-accent/50 transition-colors">
                                        <div className="flex items-center gap-4">
                                            <div className="w-8 flex justify-center">
                                                {getRankIcon(index)}
                                            </div>
                                            <div>
                                                <div className="font-bold text-lg">{entry.username}</div>
                                                <div className="text-xs text-muted-foreground">{getTitle(entry.level)} (Lvl {entry.level})</div>
                                            </div>
                                        </div>
                                        <div className="font-mono font-bold text-primary">
                                            {entry.xp} XP
                                        </div>
                                    </div>
                                ))}
                                {entries.length === 0 && (
                                    <div className="text-center text-muted-foreground py-4">Henüz veri yok.</div>
                                )}
                            </div>
                        </ScrollArea>
                    )}
                </CardContent>
            </Card>

        </div>
    )
}
