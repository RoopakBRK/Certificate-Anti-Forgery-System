// Backend Schema Types - Matching app/schemas.py

export interface ForensicsResult {
    manipulation_score: number;
    is_high_risk: boolean;
    status: string;
    inconclusive?: boolean;
    details?: string[] | null;
    llm_analysis?: string | null;
    llm_risk_score?: number | null;
    llm_confidence?: number | null;
    llm_reasoning?: string | null;
}

export interface ExtractionResult {
    candidate_name?: string | null;
    certificate_id?: string | null;
    issuer_url?: string | null;
    issuer_name?: string | null;
    issuer_org?: string | null;
    raw_text_snippet?: string | null;
    certificate_date?: string | null;
}

export interface VerificationResult {
    is_verified: boolean;
    message: string;
    trusted_domain: boolean;
    confidence_score?: number;
    verification_url?: string | null;
    method?: string;
}

export interface CertificateAnalysisResponse {
    filename: string;
    final_verdict: string;
    forensics: ForensicsResult;
    extraction: ExtractionResult;
    verification: VerificationResult;
    /** Server-signed proof, only present for VERIFIED results */
    report_token?: string | null;
}

/** Payload of a signed report, as returned by GET /report */
export interface ReportPayload {
    valid: boolean;
    scope: 'document' | 'id_only';
    verdict: string;
    candidate_name?: string | null;
    certificate_id?: string | null;
    issuer_name?: string | null;
    verification_url?: string | null;
    method?: string;
    forensics_status?: string;
    verified_at: number;
}

// Manual Verification Types
export interface ManualVerificationRequest {
    certificate_id: string;
    issuer_url: string;
}

export interface ApiError {
    detail: string;
}
