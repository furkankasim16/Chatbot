"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogIn, UserPlus, AlertCircle } from "lucide-react"

interface AuthScreenProps {
  onLogin: (username: string, password: string) => Promise<void>
  onRegister: (username: string, email: string, password: string) => Promise<void>
}

export function AuthScreen({ onLogin, onRegister }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (mode === "register" && password !== confirmPassword) {
      setError("Şifreler eşleşmiyor")
      return
    }

    if (password.length < 6) {
      setError("Şifre en az 6 karakter olmalıdır")
      return
    }

    setIsLoading(true)

    try {
      if (mode === "login") {
        await onLogin(username, password)
      } else {
        await onRegister(username, email, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bir hata oluştu")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="animate-fade-in">
      <Card className="p-8 max-w-md mx-auto">
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <div className="w-16 h-16 rounded-xl bg-primary flex items-center justify-center mx-auto">
              {mode === "login" ? (
                <LogIn className="w-8 h-8 text-primary-foreground" />
              ) : (
                <UserPlus className="w-8 h-8 text-primary-foreground" />
              )}
            </div>
            <h2 className="text-2xl font-bold text-foreground">{mode === "login" ? "Giriş Yap" : "Kayıt Ol"}</h2>
            <p className="text-muted-foreground">
              {mode === "login"
                ? "Hesabınıza giriş yapın ve öğrenmeye devam edin"
                : "Yeni bir hesap oluşturun ve öğrenmeye başlayın"}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Kullanıcı Adı</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="kullaniciadi"
                required
                disabled={isLoading}
              />
            </div>

            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="email">E-posta</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ornek@email.com"
                  required
                  disabled={isLoading}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="password">Şifre</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
              />
            </div>

            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Şifre Tekrar</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={isLoading}
                />
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "İşleniyor..." : mode === "login" ? "Giriş Yap" : "Kayıt Ol"}
            </Button>
          </form>

          <div className="text-center">
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login")
                setError("")
              }}
              className="text-sm text-primary hover:underline"
              disabled={isLoading}
            >
              {mode === "login" ? "Hesabınız yok mu? Kayıt olun" : "Zaten hesabınız var mı? Giriş yapın"}
            </button>
          </div>
        </div>
      </Card>
    </div>
  )
}
