type Tone = "gray" | "blue" | "green" | "orange" | "red" | "purple"

export const inr = (n?: number | null, compact = false) => {
  if (n === null || n === undefined || Number.isNaN(n)) return "\u20b90"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: compact ? 1 : 0,
    notation: compact && Math.abs(n) >= 100000 ? "compact" : "standard",
  }).format(n)
}

export const num = (n?: number | null) =>
  n === null || n === undefined ? "0" : new Intl.NumberFormat("en-IN").format(n)

export const pct = (n?: number | null) => {
  if (n === null || n === undefined) return "n/a"
  const v = n <= 1 ? n * 100 : n
  return `${Math.round(v)}%`
}

export const dateFmt = (iso?: string | null) => {
  if (!iso) return "\u2014"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
}

export const dateTimeFmt = (iso?: string | null) => {
  if (!iso) return "\u2014"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export const riskTone = (level?: string): Tone => {
  switch ((level || "").toLowerCase()) {
    case "critical":
    case "high":
      return "red"
    case "medium":
    case "moderate":
      return "orange"
    case "low":
      return "green"
    default:
      return "gray"
  }
}

export const severityTone = riskTone

export const scoreTone = (score: number): Tone => (score >= 70 ? "green" : score >= 40 ? "orange" : "red")

export const titleCase = (s?: string) =>
  (s || "")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim() || "\u2014"

export const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export const download = (filename: string, content: string, mime = "text/plain") => {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export const statutoryInterest = (principal: number, months: number, rbiBankRate = 6.5) => {
  const annualRate = rbiBankRate * 3
  const monthlyRate = annualRate / 12
  const factor = Math.pow(1 + monthlyRate / 100, Math.max(0, months))
  const totalRecoverable = principal * factor
  return {
    annualRate,
    monthlyRate,
    interest: Math.max(0, totalRecoverable - principal),
    totalRecoverable,
  }
}

export const taxDisallowance = (principal: number, taxRatePercent = 25) => (principal * taxRatePercent) / 100
