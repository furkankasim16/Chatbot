"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useToast } from "@/components/ui/use-toast"
import { getStudents, type StudentStats } from "@/lib/api"
import { StudentTable } from "@/components/teacher/student-table"
import { Button } from "@/components/ui/button"
import { ArrowLeft, GraduationCap } from "lucide-react"

export default function TeacherPage() {
    const router = useRouter()
    const { toast } = useToast()
    const [students, setStudents] = useState<StudentStats[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const token = localStorage.getItem("auth_token")
        if (!token) {
            router.push("/")
            return
        }

        getStudents(token)
            .then(setStudents)
            .catch((err) => {
                toast({
                    title: "Hata",
                    description: err.message,
                    variant: "destructive",
                })
            })
            .finally(() => setLoading(false))
    }, [router, toast])

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background text-foreground">
                Yükleniyor...
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-background text-foreground p-8">
            <div className="mx-auto max-w-5xl space-y-8">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => router.push("/")}
                            className="rounded-full"
                        >
                            <ArrowLeft className="h-5 w-5" />
                        </Button>
                        <div>
                            <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
                                <GraduationCap className="h-8 w-8 text-primary" />
                                Öğretmen Paneli
                            </h1>
                            <p className="text-muted-foreground">
                                Öğrenci durumlarını ve sınıf performansını takip edin.
                            </p>
                        </div>
                    </div>
                </div>

                <StudentTable students={students} />
            </div>
        </div>
    )
}
