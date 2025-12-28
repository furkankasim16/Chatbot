"use client"

import { useState } from "react"
import { uploadDocument } from "@/lib/api"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, UploadCloud, FileText, CheckCircle2 } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

interface KnowledgeBaseUploadModalProps {
    isOpen: boolean
    onClose: () => void
    token: string
}

export function KnowledgeBaseUploadModal({
    isOpen,
    onClose,
    token,
}: KnowledgeBaseUploadModalProps) {
    const { toast } = useToast()
    const [file, setFile] = useState<File | null>(null)
    const [topic, setTopic] = useState("general")
    const [isUploading, setIsUploading] = useState(false)
    const [uploadStats, setUploadStats] = useState<{
        filename: string
        chunks: number
    } | null>(null)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
            setUploadStats(null)
        }
    }

    const handleUpload = async () => {
        if (!file) return

        setIsUploading(true)
        try {
            const res = await uploadDocument(token, file, topic)
            setUploadStats({
                filename: res.filename,
                chunks: res.chunks_count,
            })
            toast({
                title: "Yükleme Başarılı! 🎉",
                description: `${res.filename} başarıyla bilgi bankasına eklendi (${res.chunks_count} parça).`,
                variant: "default", // You might have a "success" variant
            })
            setFile(null)
        } catch (error: any) {
            toast({
                title: "Yükleme Hatası",
                description: error.message || "Bilinmeyen bir hata oluştu.",
                variant: "destructive",
            })
        } finally {
            setIsUploading(false)
        }
    }

    const handleClose = () => {
        setFile(null)
        setUploadStats(null)
        setTopic("general")
        onClose()
    }

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Bilgi Bankasına Belge Ekle</DialogTitle>
                    <DialogDescription>
                        Kendi PDF dökümanlarını yükleyerek asistanı eğitebilirsin.
                    </DialogDescription>
                </DialogHeader>

                {!uploadStats ? (
                    <div className="grid gap-4 py-4">
                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <Label htmlFor="pdf-file">PDF Dosyası</Label>
                            <div className="flex items-center gap-2">
                                <Input
                                    id="pdf-file"
                                    type="file"
                                    accept="application/pdf"
                                    onChange={handleFileChange}
                                    disabled={isUploading}
                                />
                            </div>
                        </div>

                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <Label htmlFor="topic">Konu (Opsiyonel)</Label>
                            <Input
                                id="topic"
                                type="text"
                                placeholder="Örn: Siber Güvenlik"
                                value={topic}
                                onChange={(e) => setTopic(e.target.value)}
                                disabled={isUploading}
                            />
                        </div>
                    </div>
                ) : (
                    <div className="py-6 flex flex-col items-center justify-center space-y-3 text-center animate-in fade-in zoom-in duration-300">
                        <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                            <CheckCircle2 className="w-8 h-8 text-green-600 dark:text-green-400" />
                        </div>
                        <h3 className="text-lg font-semibold">İşlem Tamamlandı!</h3>
                        <p className="text-sm text-muted-foreground">
                            <b>{uploadStats.filename}</b> dosyası parçalandı ve indekslendi.
                            <br />
                            Toplam <b>{uploadStats.chunks}</b> bilgi parçacığı eklendi.
                        </p>
                        <Button variant="outline" size="sm" onClick={() => setUploadStats(null)}>
                            Yeni Dosya Yükle
                        </Button>
                    </div>
                )}

                <DialogFooter className="sm:justify-end">
                    <Button type="button" variant="secondary" onClick={handleClose} disabled={isUploading}>
                        Kapat
                    </Button>
                    {!uploadStats && (
                        <Button type="button" onClick={handleUpload} disabled={!file || isUploading}>
                            {isUploading ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Yükleniyor...
                                </>
                            ) : (
                                <>
                                    <UploadCloud className="w-4 h-4 mr-2" />
                                    Yükle & Eğit
                                </>
                            )}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
