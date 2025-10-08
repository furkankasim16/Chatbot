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
import { User, BarChart3, LogOut, Shield } from "lucide-react"

interface UserMenuProps {
  username: string
  isAdmin?: boolean
  onViewStats: () => void
  onViewAdminPanel?: () => void
  onLogout: () => void
}

export function UserMenu({ username, isAdmin, onViewStats, onViewAdminPanel, onLogout }: UserMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="rounded-full bg-transparent">
          <User className="w-5 h-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{username}</p>
            <p className="text-xs leading-none text-muted-foreground">Hoş geldiniz!</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onViewStats} className="cursor-pointer">
          <BarChart3 className="w-4 h-4 mr-2" />
          İstatistiklerim
        </DropdownMenuItem>
        {isAdmin && onViewAdminPanel && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onViewAdminPanel} className="cursor-pointer">
              <Shield className="w-4 h-4 mr-2" />
              Admin Panel
            </DropdownMenuItem>
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
