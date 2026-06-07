"use client";

/**
 * NarrationStage is the all-in-one narrated content component.
 *
 * It composes NarrationPlayer (audio), HighlightedText (visual sync),
 * and NarrationControls (play/pause/speed) into a single glass card.
 *
 * Usage:
 *   <NarrationStage
 *     chunks={narrationChunks}
 *     variant="glow"
 *     autoPlay
 *   />
 *
 * The coaching agent's present_content tool provides the chunks array.
 * Each chunk has: { content_hash, audio_url, text, duration_ms, word_timings }
 * Plus optional: { highlight } for key terms.
 */

import { NarrationPlayer, type NarrationChunkData } from "./NarrationPlayer";
import { HighlightedText } from "./HighlightedText";
import { NarrationControls } from "./NarrationControls";

interface NarrationStageProps {
    chunks: (NarrationChunkData & { highlight?: string })[];
    variant?: "glow" | "underline" | "fill" | "minimal";
    autoPlay?: boolean;
    showAllChunks?: boolean;
    onComplete?: () => void;
    className?: string;
}

export function NarrationStage({
    chunks,
    variant = "glow",
    autoPlay = false,
    showAllChunks = true,
    onComplete,
    className = "",
}: NarrationStageProps) {
    if (!chunks || chunks.length === 0) return null;

    return (
        <NarrationPlayer
            chunks={chunks}
            autoPlay={autoPlay}
            onComplete={onComplete}
        >
            <div className={`ns-stage glass ${className}`}>
                <div className="ns-text">
                    <HighlightedText
                        chunks={chunks.map((c) => ({
                            text: c.text,
                            word_timings: c.word_timings,
                            highlight: c.highlight,
                        }))}
                        variant={variant}
                        showAll={showAllChunks}
                    />
                </div>

                <NarrationControls totalChunks={chunks.length} />
            </div>
        </NarrationPlayer>
    );
}
