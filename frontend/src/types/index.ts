export type EvidenceItem = {
  source_text: string
  clause_reference?: string
  page_number?: number
  statute_ref?: string
  matched_keywords?: string[]
}

export type FinancialImpact = {
  estimated_delay_days?: number
  statutory_interest_rate_percent?: number
  estimated_interest_exposure?: number
  tax_disallowance_risk?: boolean
  estimated_tax_exposure?: number
  total_financial_exposure?: number
  months_overdue?: number
  monthly_compound_rate?: number
  rbi_bank_rate?: number
  principal_amount?: number
  total_recoverable?: number
  calculation_method?: string
}

export type ViolationItem = {
  clause_text: string
  violation_type: string
  cited_law: string
  cited_chunk_id?: string
  severity: string
  draft_counter_clause?: string
  samadhaan_ready?: boolean
  evidence?: EvidenceItem
  financial_impact?: FinancialImpact
  confidence?: number
  needs_human_review?: boolean
  reviewer_action?: string
}

export type ReviewDecisionSchema = {
  needs_human_review: boolean
  review_reasons: string[]
  confidence_score: number
  auto_approved: boolean
  flags?: string[]
  recommended_action?: string
}

export type RiskScoreBreakdown = {
  deduction_name: string
  points_deducted: number
  rationale: string
  triggered: boolean
}

export type RecommendedActionSchema = {
  action_id: string
  label: string
  effort_level: string
  is_recommended: boolean
  reason: string
  escalation_order: number
}

export type NegotiationRecommendation = {
  original_clause: string
  violation_type: string
  cited_law: string
  compliant_replacement: string
  risk_explanation: string
  confidence: number
}

export type AnalysisReport = {
  report_id: string
  buyer_name: string
  file_name: string
  compliance_score: number
  risk_level: string
  violations: ViolationItem[]
  overall_summary: string
  draft_samadhaan_complaint?: string
  analyzed_at: string
  financial_summary?: FinancialImpact
  review_decision?: ReviewDecisionSchema
  disclaimer?: string
  risk_score_breakdown?: RiskScoreBreakdown[]
  risk_score_disclaimer?: string
  recommended_actions?: RecommendedActionSchema[]
  contact_attempts?: number
  first_contact_date?: string
  negotiation_recommendations?: NegotiationRecommendation[]
  financial_breakdown?: Record<string, unknown>
}

export type HistoryRow = {
  id: string
  buyer_name: string
  file_name: string
  compliance_score: number
  violations_count: number
  created_at: string
  report_data: AnalysisReport
}

export type ContactActionResponse = {
  report_id: string
  contact_attempts: number
  first_contact_date?: string
  recommended_actions: RecommendedActionSchema[]
}

export type HealthResponse = {
  status: string
  model?: string
  langsmith_enabled?: boolean
  langsmith_project?: string
  rag_total_documents?: number
}

export type ChatResponse = {
  output: string
  route: string
  context?: string
  chat_id: string
  user_id: string
  eval_scores?: Record<string, unknown>
}

export type PlanLimits = {
  analyses: number
  documents: number
  chat_messages: number
  api_access: boolean
  price_inr: number
  name: string
}

export type OrgUsage = {
  org_id?: string
  plan: string
  usage: { analyses: number; documents: number; chat_messages: number }
  limits: PlanLimits
}

export type Organization = {
  org_id: string
  name: string
  plan: string
  member_count: number
  members: Array<{ email: string; role: string; status: string }>
}

export type ApiKey = {
  key_id: string
  name: string
  key_prefix: string
  created_at: string
  last_used_at?: string | null
  revoked?: boolean
}

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  route?: string
  streaming?: boolean
}
