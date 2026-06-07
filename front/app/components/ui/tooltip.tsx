"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}

function Tooltip({
  children,
  content,
  containerClassName,
  className,
}: {
  children: React.ReactNode
  content?: React.ReactNode
  containerClassName?: string
  className?: string
}) {
  return (
    <span className={cn("group/tooltip relative inline-flex", containerClassName)}>
      {children}
      {content ? <TooltipContent className={className}>{content}</TooltipContent> : null}
    </span>
  )
}

function TooltipTrigger({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span className={cn("inline-flex", className)} {...props}>
      {children}
    </span>
  )
}

function TooltipContent({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden w-max max-w-xs -translate-x-1/2 rounded-md bg-foreground px-3 py-1.5 text-xs text-background shadow-lg group-hover/tooltip:block group-focus-within/tooltip:block",
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
