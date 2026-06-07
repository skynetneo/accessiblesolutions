"use client";

import { useNarration } from "./NarrationPlayer";

interface NarrationControlsProps {
    totalChunks: number;
    className?: string;
    compact?: boolean;
}

export function NarrationControls({
    totalChunks,
    className = "",
    compact = false,
}: NarrationControlsProps) {
    const {
        state,
        currentChunk,
        totalElapsed,
        totalDuration,
        speed,
        toggle,
        skipTo,
        setSpeed,
    } = useNarration();

    const progress = totalDuration > 0 ? (totalElapsed / totalDuration) * 100 : 0;

    const formatTime = (ms: number) => {
        const s = Math.floor(ms / 1000);
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${m}:${sec.toString().padStart(2, "0")}`;
    };

    return (
        <div className={`nc-bar ${compact ? "nc-compact" : ""} ${className}`}>
            {/* Play / pause */}
            <button
                className="nc-play"
                onClick={toggle}
                aria-label={state === "playing" ? "Pause" : "Play"}
            >
                {state === "playing" ? (
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <rect x="3" y="2" width="4" height="12" rx="1" />
                        <rect x="9" y="2" width="4" height="12" rx="1" />
                    </svg>
                ) : (
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M4 2.5v11l9-5.5z" />
                    </svg>
                )}
            </button>

            {/* Progress bar */}
            <div className="nc-progress-track">
                <div
                    className="nc-progress-fill"
                    style={{ width: `${Math.min(progress, 100)}%` }}
                />
                {/* Chunk markers */}
                {!compact &&
                    Array.from({ length: totalChunks }, (_, i) => {
                        const chunkStart =
                            i === 0
                                ? 0
                                : /* approximate */ (i / totalChunks) * 100;
                        return (
                            <button
                                key={i}
                                className={`nc-marker ${i === currentChunk ? "nc-marker-active" : ""} ${i < currentChunk ? "nc-marker-done" : ""}`}
                                style={{ left: `${chunkStart}%` }}
                                onClick={() => skipTo(i)}
                                aria-label={`Skip to chunk ${i + 1}`}
                            />
                        );
                    })}
            </div>

            {/* Time */}
            <span className="nc-time">
                {formatTime(totalElapsed)} / {formatTime(totalDuration)}
            </span>

            {/* Speed control */}
            {!compact && (
                <button
                    className="nc-speed"
                    onClick={() => {
                        const speeds = [0.75, 1.0, 1.25, 1.5];
                        const idx = speeds.indexOf(speed);
                        const next = speeds[(idx + 1) % speeds.length];
                        setSpeed(next);
                    }}
                    aria-label={`Speed: ${speed}x`}
                >
                    {speed}x
                </button>
            )}
        </div>
    );
}
