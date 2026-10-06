import type { CertificateAnalysisResponse, ReportPayload } from '@/types';
import { getAccessToken } from '@/lib/supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (
  process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000'
);

// Verification runs OCR + forensics + a live issuer lookup, so allow a generous timeout
const REQUEST_TIMEOUT_MS = 120_000;

/** Signed-in users send their Supabase token so the result is saved to their history. */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken().catch(() => null);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error('The verification service is not configured (NEXT_PUBLIC_API_URL is missing).');
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: controller.signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The request timed out. Please try again.');
    }
    // fetch() rejects with a TypeError on network failure / CORS / server down
    throw new Error('Could not reach the verification server. Please check your connection and try again.');
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === 'string' ? body.detail : null;
    throw new Error(detail || `Request failed (HTTP ${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const verificationService = {
  async uploadCertificate(file: File): Promise<CertificateAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return request<CertificateAnalysisResponse>('/verify', { method: 'POST', body: formData, headers: await authHeaders() });
  },

  async manualVerify(data: { certificate_id: string; issuer_url: string }): Promise<CertificateAnalysisResponse> {
    return request<CertificateAnalysisResponse>('/verify/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
      body: JSON.stringify(data),
    });
  },

  /** Ask the server whether a report token is genuine and get its contents. */
  getReport(token: string): Promise<ReportPayload> {
    return request<ReportPayload>(`/report?token=${encodeURIComponent(token)}`);
  },

  async checkHealth(): Promise<boolean> {
    try {
      await request<{ status: string }>('/health');
      return true;
    } catch {
      return false;
    }
  },
};
