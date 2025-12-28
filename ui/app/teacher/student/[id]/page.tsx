"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useToast } from "@/components/ui/use-toast"
import { getStudentDetails, type StudentDetail } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { ArrowLeft, AlertTriangle, GraduationCap, Trophy } from "lucide-react"

export default function StudentDetailPage() {
    const params = useParams()
    const router = useRouter()
    const { toast } = useToast()
    const [data, setData] = useState<StudentDetail | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const token = localStorage.getItem("auth_token")
        if (!token) {
            router.push("/")
            return
        }

        const id = Number(params.id)
        if (isNaN(id)) {
            router.push("/teacher")
            return
        }

        getStudentDetails(token, id)
            .then(setData)
            .catch((err) => {
                toast({
                    title: "Hata",
                    description: err.message,
                    variant: "destructive",
                })
            })
            .finally(() => setLoading(false))
    }, [params.id, router, toast])

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background text-foreground">
                Yükleniyor...
            </div>
        )
    }

    if (!data) return null

    const handleDownloadPDF = async () => {
        if (!data) return
        const token = localStorage.getItem("auth_token")
        if (!token) return

        try {
            // Backend port 8000 varsayımı - production için env'den almalı
            const res = await fetch(`http://localhost:8000/api/v1/reports/student/${data.user.id}/pdf`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!res.ok) throw new Error("PDF oluşturulamadı")

            const blob = await res.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement("a")
            a.href = url
            a.download = `report_${data.user.username}.pdf`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)

            toast({
                title: "Başarılı",
                description: "Karne PDF olarak indirildi.",
            })
        } catch (e) {
            toast({ title: "Hata", description: "PDF indirilirken hata oluştu.", variant: "destructive" })
        }
    }

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="mx-auto max-w-5xl space-y-8">
                <div className="flex items-center gap-4">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => router.push("/teacher")}
                        className="rounded-full"
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight">{data.user.username}</h1>
                        <p className="text-muted-foreground">{data.user.email}</p>
                    </div>
                    <div className="ml-auto flex items-center gap-4">
                        <Button onClick={handleDownloadPDF} variant="outline" className="gap-2">
                            Karne İndir
                        </Button>
                        <Badge variant="secondary" className="text-sm px-3 py-1">
                            Lvl {data.user.level}
                        </Badge>
                        <Badge variant="outline" className="text-sm px-3 py-1">
                            {data.user.xp} XP
                        </Badge>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Weak Topics */}
                    <Card className="border-destructive/50 bg-destructive/5">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-destructive">
                                <AlertTriangle className="h-5 w-5" />
                                Geliştirilmesi Gereken Alanlar
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {data.weak_topics.length > 0 ? (
                                <div className="space-y-3">
                                    {data.weak_topics.map((t, i) => (
                                        <div key={i} className="flex justify-between items-center bg-background/50 p-2 rounded border">
                                            <span className="font-medium">{t.topic}</span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm text-destructive font-bold">%{t.accuracy.toFixed(0)}</span>
                                                <span className="text-xs text-muted-foreground">({t.total} soru)</span>
                                            </div>
                                        </div>
                                    ))}
                                    <p className="text-xs text-muted-foreground mt-2">
                                        * Bu konularda başarı oranı %60'ın altında.
                                    </p>
                                </div>
                            ) : (
                                <div className="text-center py-8 text-muted-foreground">
                                    <Trophy className="h-8 w-8 mx-auto mb-2 opacity-50 text-green-500" />
                                    Harika! Şu an kritik bir zayıf konu görünmüyor.
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* General Stats */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <GraduationCap className="h-5 w-5 text-primary" />
                                Genel Başarı
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {data.all_topics.slice(0, 5).map((t, i) => (
                                    <div key={i} className="flex justify-between items-center text-sm">
                                        <span>{t.topic}</span>
                                        <div className="flex items-center gap-2">
                                            <div className="w-24 h-2 bg-secondary rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full ${t.accuracy >= 70 ? 'bg-green-500' : t.accuracy >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                    style={{ width: `${t.accuracy}%` }}
                                                />
                                            </div>
                                            <span className="w-8 text-right font-medium">%{t.accuracy.toFixed(0)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Recent History */}
                <Card>
                    <CardHeader>
                        <CardTitle>Son Aktiviteler</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Tarih</TableHead>
                                    <TableHead>Konu</TableHead>
                                    <TableHead>Seviye</TableHead>
                                    <TableHead>Puan</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {data.recent_activity.map((r) => (
                                    <TableRow key={r.id}>
                                        <TableCell className="text-muted-foreground text-sm">
                                            {new Date(r.date).toLocaleString("tr-TR")}
                                        </TableCell>
                                        <TableCell className="font-medium">{r.topic}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="text-xs capitalize">
                                                {r.difficulty}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <span
                                                className={
                                                    r.score >= 70
                                                        ? "text-green-500 font-bold"
                                                        : r.score >= 50
                                                            ? "text-yellow-500 font-bold"
                                                            : "text-red-500 font-bold"
                                                }
                                            >
                                                {r.score}
                                            </span>
                                        </TableCell>
                                    </TableRow>
                                ))}
                                {data.recent_activity.length === 0 && (
                                    <TableRow>
                                        <TableCell colSpan={4} className="h-24 text-center">
                                            Henüz aktivite yok.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
