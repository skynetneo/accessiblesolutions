// app/api/extract-resume/route.ts
//
// Server-side resume text extraction with strict validation.
// Supports PDF, DOCX, TXT, and MD only.
// Enforces optional API-key auth, size limit, and PDF page cap.

import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";

interface PdfTextItem {
    str?: string;
    transform?: number[];
}

interface PdfParseResult {
    text: string;
}

type SupportedFileType = "txt" | "md" | "pdf" | "docx";

class HttpError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message);
        this.status = status;
    }
}

const DEFAULT_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5MB
const DEFAULT_MAX_PDF_PAGES = 10;

const MAX_FILE_SIZE_BYTES = parsePositiveInt(
    process.env.EXTRACT_RESUME_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_FILE_SIZE_BYTES,
);
const MAX_PDF_PAGES = parsePositiveInt(
    process.env.EXTRACT_RESUME_MAX_PDF_PAGES,
    DEFAULT_MAX_PDF_PAGES,
);

const REQUIRED_API_KEY =
    process.env.EXTRACT_RESUME_API_KEY?.trim()
    || process.env.RESUME_EXTRACT_API_KEY?.trim()
    || "";

const TYPE_BY_EXTENSION: Record<string, SupportedFileType> = {
    txt: "txt",
    md: "md",
    pdf: "pdf",
    docx: "docx",
};

const ALLOWED_MIME_BY_TYPE: Record<SupportedFileType, readonly string[]> = {
    txt: ["text/plain"],
    md: ["text/markdown", "text/x-markdown", "text/plain"],
    pdf: ["application/pdf"],
    docx: ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
};

export async function POST(req: NextRequest) {
    try {
        enforceApiKey(req);

        const formData = await req.formData();
        const file = formData.get("file") as File | null;

        if (!file) {
            return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
        }

        if (!file.name.trim()) {
            return NextResponse.json({ error: "File name is required" }, { status: 400 });
        }

        if (file.size <= 0) {
            return NextResponse.json({ error: "Uploaded file is empty" }, { status: 400 });
        }

        if (file.size > MAX_FILE_SIZE_BYTES) {
            return NextResponse.json(
                { error: `File too large. Max size is ${formatBytes(MAX_FILE_SIZE_BYTES)}.` },
                { status: 413 },
            );
        }

        const buffer = Buffer.from(await file.arrayBuffer());
        const fileType = validateFileType(file, buffer);
        let text = "";

        if (fileType === "txt" || fileType === "md") {
            text = buffer.toString("utf-8");
        } else if (fileType === "pdf") {
            text = await extractPdfText(buffer, MAX_PDF_PAGES);
        } else if (fileType === "docx") {
            text = await extractDocxText(buffer);
        }

        if (!text.trim()) {
            return NextResponse.json(
                { error: "Could not extract text from file. Try pasting your resume instead." },
                { status: 422 },
            );
        }

        return NextResponse.json({
            text: text.trim(),
            filename: file.name,
            size: file.size,
        });
    } catch (err) {
        if (err instanceof HttpError) {
            return NextResponse.json({ error: err.message }, { status: err.status });
        }

        console.error("Resume extraction error:", err);
        return NextResponse.json({ error: "Failed to process file" }, { status: 500 });
    }
}

/**
 * Extract text from a PDF using pdfjs-dist.
 *
 * pdfjs-dist handles multi-column layouts, tables, and embedded fonts.
 * Falls back to pdf-parse if pdfjs-dist fails.
 */
async function extractPdfText(buffer: Buffer, maxPdfPages: number): Promise<string> {
    const uint8 = new Uint8Array(buffer);

    // Try pdfjs-dist first (most robust)
    try {
        const pdfjsLib = await import("pdfjs-dist/legacy/build/pdf.mjs");
        const doc = await pdfjsLib.getDocument({ data: uint8 }).promise;

        if (doc.numPages > maxPdfPages) {
            throw new HttpError(
                422,
                `PDF exceeds page limit (${doc.numPages} pages, max ${maxPdfPages}).`,
            );
        }

        const pages: string[] = [];

        for (let i = 1; i <= doc.numPages; i++) {
            const page = await doc.getPage(i);
            const content = await page.getTextContent();

            // Sort text items by position (handles multi-column)
            const items = content.items as PdfTextItem[];

            // Group by Y position (same line), sort by X within line
            const lines = new Map<number, Array<{ x: number; text: string }>>();
            for (const item of items) {
                const text = item.str ?? "";
                const transform = item.transform ?? [];
                if (!text.trim() || transform.length < 6) continue;
                // transform[5] = Y position, transform[4] = X position
                const y = Math.round(transform[5]);
                const x = transform[4];
                if (!lines.has(y)) lines.set(y, []);
                lines.get(y)!.push({ x, text });
            }

            // Sort lines by Y (descending = top to bottom in PDF coords)
            const linesArr: Array<[number, Array<{ x: number; text: string }>]> = [];
            lines.forEach((items, y) => linesArr.push([y, items]));

            const sortedLines = linesArr
                .sort((a, b) => b[0] - a[0])
                .map((entry) =>
                    entry[1]
                        .sort((a, b) => a.x - b.x)
                        .map((i) => i.text)
                        .join(" ")
                );

            pages.push(sortedLines.join("\n"));
        }

        return pages.join("\n\n");
    } catch (err) {
        if (err instanceof HttpError) {
            throw err;
        }
        // Continue to fallback parser.
    }

    // Fallback: pdf-parse
    try {
        const pdfParseModule = await import("pdf-parse");
        const pdfParse = getPdfParseFn(pdfParseModule);
        if (!pdfParse) {
            throw new Error("pdf-parse module does not expose a parser");
        }
        const result = await pdfParse(buffer);
        return result.text;
    } catch {
        return "";
    }
}

/**
 * Extract text from a DOCX using mammoth.
 */
async function extractDocxText(buffer: Buffer): Promise<string> {
    try {
        const mammoth = await import("mammoth");
        const result = await mammoth.extractRawText({ buffer });
        return result.value;
    } catch {
        return "";
    }
}

function enforceApiKey(req: NextRequest): void {
    if (!REQUIRED_API_KEY) {
        return;
    }

    const headerKey = req.headers.get("x-api-key")?.trim() ?? "";
    const authorization = req.headers.get("authorization") ?? "";
    const bearerToken = authorization.toLowerCase().startsWith("bearer ")
        ? authorization.slice(7).trim()
        : "";
    const providedKey = headerKey || bearerToken;

    if (!providedKey || !constantTimeEquals(providedKey, REQUIRED_API_KEY)) {
        throw new HttpError(401, "Unauthorized");
    }
}

function constantTimeEquals(a: string, b: string): boolean {
    const aBytes = Buffer.from(a);
    const bBytes = Buffer.from(b);
    if (aBytes.length !== bBytes.length) {
        return false;
    }
    return timingSafeEqual(aBytes, bBytes);
}

function validateFileType(file: File, buffer: Buffer): SupportedFileType {
    const extension = getExtension(file.name);
    const fileType = TYPE_BY_EXTENSION[extension];
    if (!fileType) {
        throw new HttpError(415, "Unsupported file extension. Allowed: .pdf, .docx, .txt, .md");
    }

    const mime = file.type.trim().toLowerCase();
    const allowedMimes = ALLOWED_MIME_BY_TYPE[fileType];
    if (mime && !allowedMimes.includes(mime)) {
        throw new HttpError(415, `MIME type ${mime} does not match .${extension}`);
    }

    const signatureValid = (
        (fileType === "pdf" && hasPdfSignature(buffer))
        || (fileType === "docx" && hasDocxSignature(buffer))
        || ((fileType === "txt" || fileType === "md") && isLikelyUtf8Text(buffer))
    );

    if (!signatureValid) {
        throw new HttpError(415, "File signature does not match the declared file type");
    }

    return fileType;
}

function hasPdfSignature(buffer: Buffer): boolean {
    return buffer.length >= 5
        && buffer[0] === 0x25 // %
        && buffer[1] === 0x50 // P
        && buffer[2] === 0x44 // D
        && buffer[3] === 0x46 // F
        && buffer[4] === 0x2d; // -
}

function hasDocxSignature(buffer: Buffer): boolean {
    if (buffer.length < 4) {
        return false;
    }

    const isZipContainer = (
        buffer[0] === 0x50
        && buffer[1] === 0x4b
        && (
            (buffer[2] === 0x03 && buffer[3] === 0x04)
            || (buffer[2] === 0x05 && buffer[3] === 0x06)
            || (buffer[2] === 0x07 && buffer[3] === 0x08)
        )
    );

    if (!isZipContainer) {
        return false;
    }

    return buffer.includes(Buffer.from("[Content_Types].xml"))
        && buffer.includes(Buffer.from("word/"));
}

function isLikelyUtf8Text(buffer: Buffer): boolean {
    const sample = buffer.subarray(0, Math.min(buffer.length, 4096));
    if (sample.length === 0) {
        return false;
    }

    if (sample.includes(0x00)) {
        return false;
    }

    let controlCount = 0;
    for (let i = 0; i < sample.length; i += 1) {
        const byte = sample[i];
        const isAllowedControl = byte === 0x09 || byte === 0x0a || byte === 0x0d;
        if (byte < 0x20 && !isAllowedControl) {
            controlCount += 1;
        }
    }

    return controlCount / sample.length <= 0.02;
}

function getExtension(filename: string): string {
    const normalized = filename.trim().toLowerCase();
    const lastDot = normalized.lastIndexOf(".");
    if (lastDot <= 0 || lastDot === normalized.length - 1) {
        return "";
    }
    return normalized.slice(lastDot + 1);
}

function parsePositiveInt(rawValue: string | undefined, fallback: number): number {
    if (!rawValue) {
        return fallback;
    }
    const parsed = Number.parseInt(rawValue, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function formatBytes(bytes: number): string {
    if (bytes >= 1024 * 1024) {
        return `${Math.round((bytes / (1024 * 1024)) * 10) / 10}MB`;
    }
    if (bytes >= 1024) {
        return `${Math.round((bytes / 1024) * 10) / 10}KB`;
    }
    return `${bytes}B`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function getPdfParseFn(
    module: unknown,
): ((input: Buffer) => Promise<PdfParseResult>) | null {
    if (typeof module === "function") {
        return module as (input: Buffer) => Promise<PdfParseResult>;
    }

    if (isRecord(module) && typeof module.default === "function") {
        return module.default as (input: Buffer) => Promise<PdfParseResult>;
    }

    return null;
}
