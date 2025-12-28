"use client"

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { StudentStats } from "@/lib/api"
import { ExternalLink } from "lucide-react"
import { useRouter } from "next/navigation"

interface StudentTableProps {
    students: StudentStats[]
}

export function StudentTable({ students }: StudentTableProps) {
    const router = useRouter()
    return (
        <Card>
            <CardHeader>
                <CardTitle>Öğrenci Listesi ({students.length})</CardTitle>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Kullanıcı</TableHead>
                            <TableHead>Seviye</TableHead>
                            <TableHead>XP</TableHead>
                            <TableHead>Quiz</TableHead>
                            <TableHead>Ort. Puan</TableHead>
                            <TableHead>Detay</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {students.map((s) => (
                            <TableRow key={s.id}>
                                <TableCell className="font-medium">
                                    <div>{s.username}</div>
                                    <div className="text-xs text-muted-foreground">{s.email}</div>
                                </TableCell>
                                <TableCell>
                                    <Badge variant="outline" className="bg-primary/10">
                                        Lvl {s.level}
                                    </Badge>
                                </TableCell>
                                <TableCell>{s.xp} XP</TableCell>
                                <TableCell>{s.total_quizzes}</TableCell>
                                <TableCell>
                                    <span
                                        className={
                                            s.avg_score >= 70
                                                ? "text-green-500 font-bold"
                                                : s.avg_score >= 50
                                                    ? "text-yellow-500 font-bold"
                                                    : "text-red-500 font-bold"
                                        }
                                    >
                                        {s.avg_score}
                                    </span>
                                </TableCell>
                                <TableCell>
                                    <button
                                        onClick={() => router.push(`/teacher/student/${s.id}`)}
                                        className="text-muted-foreground hover:text-primary"
                                    >
                                        <ExternalLink className="h-4 w-4" />
                                    </button>
                                </TableCell>
                            </TableRow>
                        ))}
                        {students.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} className="h-24 text-center">
                                    Henüz öğrenci yok.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    )
}
