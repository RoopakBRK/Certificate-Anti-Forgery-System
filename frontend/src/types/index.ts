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

export interface OCRFieldAgreement {
    value?: string | null;
    source: string;          // llm | llm+consensus | consensus | heuristic
    votes: number;           // OCR sources that read this value
    engines: string[];
    agreement: number;       // votes / sources
}

export interface OCREngineStatus {
    name: string;
    ok: boolean;
    chars: number;
    seconds: number;
    confidence?: number | null;
    error?: string | null;
}

/** How the parallel OCR engines agreed on the extracted fields */
export interface OCRReport {
    mode: 'llm' | 'heuristic';
    engines: OCREngineStatus[];
    engines_used: string[];
    sources: number;
    visible_words: number;
    qr_codes: string[];
    certificate_id: OCRFieldAgreement;
    candidate_name: OCRFieldAgreement;
    warnings: string[];
}

export interface ExtractionResult {
    candidate_name?: string | null;
    certificate_id?: string | null;
    issuer_url?: string | null;
    issuer_name?: string | null;
    issuer_org?: string | null;
    raw_text_snippet?: string | null;
    certificate_date?: string | null;
    ocr?: OCRReport | null;
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
    /** cafs_reports row id when the user is signed in */
    report_id?: string | null;
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

/** Row of public.cafs_reports (Supabase) */
export interface CafsReport {
    id: string;
    mode: 'upload' | 'manual';
    filename: string | null;
    final_verdict: string;
    candidate_name: string | null;
    certificate_id: string | null;
    issuer_name: string | null;
    verification_url: string | null;
    is_verified: boolean;
    is_high_risk: boolean;
    report_token: string | null;
    created_at: string;
}

/** Row of public.issuers (Supabase) */
export interface Issuer {
    id: number;
    name: string;
    category: string;
    aliases: string[];
    website_url: string | null;
    verification_url: string | null;
    url_patterns: string[];
    id_example: string | null;
    verification_type: 'direct' | 'lookup';
    notes: string | null;
}
