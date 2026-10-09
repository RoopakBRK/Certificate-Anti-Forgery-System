# CAFS — Certificate Anti Forgery System

CAFS checks whether a course or training certificate is genuine. You upload a certificate (PDF, PNG, JPG or WebP) and it tells you whether the document has been tampered with and whether the issuer actually has a record of it.

It is aimed at anyone who has to trust a certificate they did not issue: recruiters, colleges, and the certificate holders themselves.

## How it works

Every upload goes through four checks, and a forged certificate has to get past all of them:

1. **Forensic scan.** Error-level analysis and the TruFor model look for regions of the image that were pasted in or edited. For PDFs, the file structure is also inspected for text typed over the original certificate in a PDF editor.
2. **Reading the details.** Several OCR engines (Tesseract, PaddleOCR, EasyOCR, optionally Mistral OCR) read the page in parallel, along with any QR code and PDF text layer. Their results are compared, and an LLM structures the text into the holder's name, the certificate ID and the issuer. Optionally, a vision model reads the page image at the same time; its reading is checked against the OCR results, and it is never waited for, so it does not slow a verification down.
3. **Confirming with the issuer.** The issuer's own verification page is opened and checked for the same certificate ID and holder name. Only issuers in a trusted registry (Coursera, Udemy, edX, LinkedIn Learning and others) are contacted.
4. **Verdict.** The results are combined into one of three outcomes.

| Verdict | Meaning |
|---|---|
| **Verified** | Clean forensic scan, and the ID and name match on the issuer's site. |
| **Unverified** | Could not be confirmed with the issuer. |
| **Flagged** | Signs of editing were found. |

A certificate is never marked Verified if the forensic scan could not complete.

## Other features

- **Manual check.** If automatic verification fails, you can enter a certificate ID and the issuer's URL yourself.
- **Shareable reports.** A verified result produces a signed report link that others can open to confirm the verdict came from CAFS.
- **History.** Signed-in users get their past verifications saved to their profile.

## What's in this repo

- `backend/` — FastAPI service that runs the forensics, OCR and issuer verification pipeline.
- `frontend/` — Next.js web app for uploading certificates and viewing results.
