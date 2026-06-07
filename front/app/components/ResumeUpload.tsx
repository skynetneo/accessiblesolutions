"use client";

import { useState, useCallback, useRef } from "react";

interface ResumeUploadProps {
    onResumeText: (text: string, method: "paste" | "upload") => void;
    onSkip: () => void;
}

const MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024; // keep aligned with API default
const ALLOWED_EXTENSIONS = new Set(["pdf", "docx", "txt", "md"]);

function getFileExtension(filename: string): string {
    const normalized = filename.trim().toLowerCase();
    const idx = normalized.lastIndexOf(".");
    if (idx <= 0 || idx === normalized.length - 1) {
        return "";
    }
    return normalized.slice(idx + 1);
}

function isSupportedResumeFile(file: File): boolean {
    return ALLOWED_EXTENSIONS.has(getFileExtension(file.name));
}

export function ResumeUpload({ onResumeText, onSkip }: ResumeUploadProps) {
    const [mode, setMode] = useState<"choose" | "paste" | "upload">("choose");
    const [pasteText, setPasteText] = useState("");
    const [uploading, setUploading] = useState(false);
    const [fileName, setFileName] = useState("");
    const fileInputRef = useRef<HTMLInputElement | null>(null);

    const handleFileUpload = useCallback(async (file: File) => {
        if (!isSupportedResumeFile(file)) {
            alert("Please upload a PDF, DOCX, TXT, or MD file.");
            return;
        }
        if (file.size <= 0) {
            alert("The selected file is empty.");
            return;
        }
        if (file.size > MAX_UPLOAD_SIZE_BYTES) {
            alert("That file is too large. Please upload a file smaller than 5MB.");
            return;
        }

        setUploading(true);
        setFileName(file.name);

        try {
            const formData = new FormData();
            formData.append("file", file);
            const res = await fetch("/api/extract-resume", {
                method: "POST",
                body: formData,
            });
            if (!res.ok) {
                let errorMessage = "Failed to extract resume text";
                try {
                    const errorData = await res.json();
                    if (
                        typeof errorData === "object"
                        && errorData !== null
                        && "error" in errorData
                        && typeof errorData.error === "string"
                    ) {
                        errorMessage = errorData.error;
                    }
                } catch {
                    // Non-JSON error payload; keep default error message.
                }
                throw new Error(errorMessage);
            }
            const data = await res.json();
            if (typeof data.text !== "string" || !data.text.trim()) {
                throw new Error("No resume text was returned");
            }

            const text = data.text.trim();
            if (!text) {
                throw new Error("No resume text could be extracted");
            }

            onResumeText(text, "upload");
        } catch (err) {
            console.error("Failed to extract resume text:", err);
            alert("Couldn't read that file. Try pasting the text instead.");
            setMode("paste");
        } finally {
            setUploading(false);
        }
    }, [onResumeText]);

    if (mode === "choose") {
        return (
            <div className="space-y-3 p-4 border rounded-xl bg-gray-50">
                <p className="text-sm text-gray-600">
                    How would you like to share your work history?
                </p>
                <div className="grid grid-cols-1 gap-2">
                    <button
                        type="button"
                        onClick={() => setMode("upload")}
                        className="flex items-center gap-3 p-3 border rounded-lg
                                   bg-white hover:bg-blue-50 transition text-left"
                    >
                        <span className="text-2xl">📄</span>
                        <div>
                            <div className="font-medium">Upload a resume</div>
                            <div className="text-xs text-gray-500">PDF, Word, or text file</div>
                        </div>
                    </button>
                    <button
                        type="button"
                        onClick={() => setMode("paste")}
                        className="flex items-center gap-3 p-3 border rounded-lg
                                   bg-white hover:bg-blue-50 transition text-left"
                    >
                        <span className="text-2xl">📋</span>
                        <div>
                            <div className="font-medium">Paste resume text</div>
                            <div className="text-xs text-gray-500">Copy from any document</div>
                        </div>
                    </button>
                    <button
                        type="button"
                        onClick={onSkip}
                        className="flex items-center gap-3 p-3 border rounded-lg
                                   bg-white hover:bg-gray-50 transition text-left"
                    >
                        <span className="text-2xl">💬</span>
                        <div>
                            <div className="font-medium">Just talk through it</div>
                            <div className="text-xs text-gray-500">
                                No resume? No problem.
                            </div>
                        </div>
                    </button>
                </div>
            </div>
        );
    }

    if (mode === "paste") {
        return (
            <div className="space-y-3 p-4 border rounded-xl bg-gray-50">
                <p className="text-sm text-gray-600">
                    Paste your resume text below. Don&apos;t worry about formatting.
                </p>
                <textarea
                    value={pasteText}
                    onChange={(e) => setPasteText(e.target.value)}
                    placeholder="Paste your resume here..."
                    className="w-full h-48 p-3 border rounded-lg text-sm font-mono
                               resize-y focus:ring-2 focus:ring-blue-300"
                />
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={() => onResumeText(pasteText, "paste")}
                        disabled={!pasteText.trim()}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg
                                   hover:bg-blue-600 disabled:opacity-50"
                    >
                        Submit
                    </button>
                    <button
                        type="button"
                        onClick={() => setMode("choose")}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800"
                    >
                        Back
                    </button>
                </div>
            </div>
        );
    }

    // Upload mode
    return (
        <div className="space-y-3 p-4 border rounded-xl bg-gray-50">
            <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                    e.preventDefault();
                    const file = e.dataTransfer.files[0];
                    if (file) handleFileUpload(file);
                }}
                role="button"
                tabIndex={0}
                aria-label="Upload resume file"
                className="border-2 border-dashed rounded-lg p-8 text-center
                           hover:border-blue-400 transition cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-300"
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        fileInputRef.current?.click();
                    }
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    className="hidden"
                    onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileUpload(file);
                    }}
                />
                {uploading ? (
                    <div className="animate-pulse">
                        <p className="text-lg">Processing {fileName}...</p>
                    </div>
                ) : (
                    <>
                        <p className="text-lg">📄 Drop your resume here</p>
                        <p className="text-sm text-gray-500 mt-1">
                            or click to browse (PDF, DOCX, TXT, MD)
                        </p>
                    </>
                )}
            </div>
            <button
                onClick={() => setMode("choose")}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
                Back
            </button>
        </div>
    );
}
