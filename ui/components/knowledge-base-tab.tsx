import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, Database, FolderSearch, RefreshCw, Trash2, CheckCircle2, UploadCloud } from "lucide-react"
import { scanCorpus, resetKnowledgeBase, uploadPdfToRag } from "@/lib/api"
import { toast } from "sonner"

interface KnowledgeBaseTabProps {
    token: string
}

export function KnowledgeBaseTab({ token }: KnowledgeBaseTabProps) {
    console.log("Rendering KnowledgeBaseTab (New Version)")
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<{ message: string; files: string[]; total_chunks?: number } | null>(null)

    // Upload states
    const [uploadFile, setUploadFile] = useState<File | null>(null)
    const [uploadTopic, setUploadTopic] = useState("general")
    const [isUploading, setIsUploading] = useState(false)

    const handleScan = async () => {
        setLoading(true)
        setResult(null)
        try {
            const res = await scanCorpus(token)
            setResult({
                message: res.message,
                files: res.files || [],
                total_chunks: res.total_chunks
            })
            toast.success("Bilgi bankası güncellendi")
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Tarama başarısız")
        } finally {
            setLoading(false)
        }
    }

    const handleReset = async () => {
        if (!confirm("Tüm indeks silinecek. Emin misiniz?")) return

        setLoading(true)
        setResult(null)
        try {
            const res = await resetKnowledgeBase(token)
            toast.success(res.message)
            setResult({ message: "Veritabanı temizlendi.", files: [] })
        } catch (err) {
            toast.error("Sıfırlama başarısız")
        } finally {
            setLoading(false)
        }
    }

    const handleUpload = async () => {
        if (!uploadFile) {
            toast.error("Lütfen bir dosya seçin")
            return
        }

        setIsUploading(true)
        try {
            const res = await uploadPdfToRag(token, uploadFile, uploadTopic)
            toast.success(`Dosya yüklendi ve indekslendi (${res.chunks_count} parça)`)
            setResult({
                message: `Yüklendi: ${res.filename}`,
                files: [res.filename],
                total_chunks: res.chunks_count
            })
            setUploadFile(null)
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "Yükleme başarısız")
        } finally {
            setIsUploading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="grid gap-6 md:grid-cols-2">
                {/* Upload Card */}
                <Card className="p-6 space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <UploadCloud className="w-5 h-5 text-primary" />
                        <h3 className="font-semibold text-lg">Yeni Doküman Yükle</h3>
                    </div>

                    <div className="space-y-3">
                        <div className="space-y-1">
                            <Label>PDF Dosyası</Label>
                            <Input
                                type="file"
                                accept="application/pdf"
                                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                            />
                        </div>

                        <div className="space-y-1">
                            <Label>Konu Etiketi</Label>
                            <Input
                                value={uploadTopic}
                                onChange={(e) => setUploadTopic(e.target.value)}
                                placeholder="Örn: security_policy"
                            />
                        </div>

                        <Button
                            onClick={handleUpload}
                            disabled={isUploading || !uploadFile}
                            className="w-full"
                        >
                            {isUploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <UploadCloud className="w-4 h-4 mr-2" />}
                            Yükle ve İndeksle
                        </Button>
                    </div>
                </Card>

                {/* Scan & Maintenance Card */}
                <Card className="p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <Database className="w-5 h-5 text-primary" />
                        <h3 className="font-semibold text-lg">Sunucu Dosyalarını Tara</h3>
                    </div>

                    <p className="text-sm text-muted-foreground mb-4">
                        <code>app/data/corpus</code> klasöründeki dosyaları topluca tarar.
                    </p>

                    <div className="flex gap-4">
                        <Button
                            onClick={handleScan}
                            disabled={loading}
                            className="flex-1"
                            variant="secondary"
                        >
                            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FolderSearch className="w-4 h-4 mr-2" />}
                            Klasörü Tara
                        </Button>

                        <Button
                            onClick={handleReset}
                            disabled={loading}
                            variant="destructive"
                            size="icon"
                            title="Veritabanını Sıfırla"
                        >
                            <Trash2 className="w-4 h-4" />
                        </Button>
                    </div>

                    {/* Status Feedback */}
                    <div className="mt-6 pt-6 border-t">
                        <div className="flex items-center gap-2 mb-2">
                            <RefreshCw className="w-4 h-4 text-muted-foreground" />
                            <span className="text-sm font-medium">Son İşlem Durumu</span>
                        </div>

                        {!result && !loading && !isUploading && (
                            <p className="text-xs text-muted-foreground italic">İşlem bekleniyor...</p>
                        )}

                        {result && (
                            <div className="p-3 bg-muted/50 rounded-lg text-sm">
                                <div className="flex items-center gap-2 text-green-600 dark:text-green-400 font-medium mb-1">
                                    <CheckCircle2 className="w-4 h-4" />
                                    {result.message}
                                </div>
                                {result.files.length > 0 && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                        Dosyalar: {result.files.join(", ")}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    )
}
