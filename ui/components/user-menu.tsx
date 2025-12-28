"use client"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { User, BarChart3, LogOut, Shield, Trophy, GraduationCap, UploadCloud } from "lucide-react"

interface UserMenuProps {
  username: string
  isAdmin?: boolean
  xp?: number
  level?: number
  onViewStats: () => void
  onViewLeaderboard: () => void
  onViewAdminPanel?: () => void
  onViewTeacherPanel?: () => void
  onViewKnowledgeBase?: () => void // New prop
  onLogout: () => void
}

export function UserMenu({ username, isAdmin, xp = 0, level = 1, onViewStats, onViewLeaderboard, onViewAdminPanel, onViewTeacherPanel, onViewKnowledgeBase, onLogout }: UserMenuProps) {
  // Simple progress: (xp % 500) / 500 * 100
  const progress = ((xp % 500) / 500) * 100

  const getRank = (lvl: number) => {
    if (lvl >= 20) return "🔮 Kâhin"
    if (lvl >= 10) return "🧠 Bilgin"
    if (lvl >= 5) return "🎓 Mezun"
    if (lvl >= 3) return "🤓 Meraklı"
    return "🐣 Çırak"
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="rounded-full bg-transparent w-auto px-2 gap-2 border-primary/20 hover:bg-primary/5">
          <div className="flex flex-col items-end hidden sm:flex">
            <span className="text-xs font-bold text-primary">{getRank(level)}</span>
            <div className="w-12 h-1 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <User className="w-5 h-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56 z-50 glass-card">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{username}</p>
            <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
              <span>Level {level}</span>
              <span>{xp} XP</span>
            </div>
            <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden mt-1">
              <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onViewStats} className="cursor-pointer">
          <BarChart3 className="w-4 h-4 mr-2" />
          İstatistiklerim
        </DropdownMenuItem>
        <DropdownMenuItem onClick={onViewLeaderboard} className="cursor-pointer">
          <Trophy className="w-4 h-4 mr-2" />
          Liderlik Tablosu
        </DropdownMenuItem>

        {isAdmin && onViewAdminPanel && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onViewAdminPanel} className="cursor-pointer">
              <Shield className="w-4 h-4 mr-2" />
              Admin Panel
            </DropdownMenuItem>

            {/* RAG Upload - Admin Only */}
            {onViewKnowledgeBase && (
              <DropdownMenuItem onClick={onViewKnowledgeBase} className="cursor-pointer">
                <UploadCloud className="w-4 h-4 mr-2" />
                Bilgi Yükle (RAG)
              </DropdownMenuItem>
            )}

            {onViewTeacherPanel && (
              <DropdownMenuItem onClick={onViewTeacherPanel} className="cursor-pointer">
                <GraduationCap className="w-4 h-4 mr-2" />
                Öğretmen Paneli
              </DropdownMenuItem>
            )}
          </>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onLogout} className="cursor-pointer text-destructive">
          <LogOut className="w-4 h-4 mr-2" />
          Çıkış Yap
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
