"use client";

import {
    useState,
    useEffect,
    useRef,
    useCallback,
    createContext,
    useContext,
} from "react";

// ── Types ────────────────────────────────────────────────────

export interface WordTiming {
    word: string;
    start_ms: number;
    end_ms: number;
}

export interface NarrationChunkData {
    content_hash: string;
    audio_url: string;
    text: string;
    duration_ms: number;
    word_timings: WordTiming[];
    cached?: boolean;
}

export type PlaybackState = "idle" | "loading" | "playing" | "paused" | "ended";

export interface NarrationContext {
    /** Current playback state */
    state: PlaybackState;
    /** Index of the currently playing chunk */
    currentChunk: number;
    /** Index of the currently highlighted word within the chunk */
    currentWord: number;
    /** Elapsed time in current chunk (ms) */
    chunkElapsed: number;
    /** Total elapsed across all chunks (ms) */
    totalElapsed: number;
    /** Total duration of all chunks (ms) */
    totalDuration: number;
    /** Playback speed multiplier */
    speed: number;
    /** Play / resume */
    play: () => void;
    /** Pause */
    pause: () => void;
    /** Toggle play/pause */
    toggle: () => void;
    /** Skip to a specific chunk */
    skipTo: (chunkIndex: number) => void;
    /** Set playback speed */
    setSpeed: (speed: number) => void;
}

const NarrationCtx = createContext<NarrationContext | null>(null);

export function useNarration() {
    const ctx = useContext(NarrationCtx);
    if (!ctx) throw new Error("useNarration must be inside <NarrationPlayer>");
    return ctx;
}

// ── Props ────────────────────────────────────────────────────

interface NarrationPlayerProps {
    /** Ordered audio chunks from the narration API */
    chunks: NarrationChunkData[];
    /** Auto-play when chunks load */
    autoPlay?: boolean;
    /** Silence between chunks (ms) */
    gapMs?: number;
    /** Initial speed */
    speed?: number;
    /** Callback when all chunks finish */
    onComplete?: () => void;
    /** Callback on each chunk start */
    onChunkStart?: (index: number) => void;
    /** Children receive narration context */
    children: React.ReactNode;
}

// ── Component ────────────────────────────────────────────────

export function NarrationPlayer({
    chunks,
    autoPlay = false,
    gapMs = 400,
    speed: initialSpeed = 1.0,
    onComplete,
    onChunkStart,
    children,
}: NarrationPlayerProps) {
    const [state, setState] = useState<PlaybackState>(
        autoPlay && chunks.length > 0 ? "loading" : "idle",
    );
    const [currentChunk, setCurrentChunk] = useState(0);
    const [currentWord, setCurrentWord] = useState(-1);
    const [chunkElapsed, setChunkElapsed] = useState(0);
    const [speed, setSpeed] = useState(initialSpeed);

    const audioRef = useRef<HTMLAudioElement | null>(null);
    const rafRef = useRef<number>(0);

    const totalDuration = chunks.reduce((sum, c) => sum + c.duration_ms, 0);

    // Compute total elapsed from chunk index + chunk elapsed
    const priorDuration = chunks
        .slice(0, currentChunk)
        .reduce((sum, c) => sum + c.duration_ms, 0);
    const totalElapsed = priorDuration + chunkElapsed;

    // ── Audio element management ─────────────────────────────

    const loadChunk = useCallback(
        (index: number) => {
            if (index >= chunks.length) {
                setState("ended");
                onComplete?.();
                return;
            }

            const chunk = chunks[index];
            setCurrentChunk(index);
            setCurrentWord(-1);
            setChunkElapsed(0);
            onChunkStart?.(index);

            // Create or reuse audio element
            if (!audioRef.current) {
                audioRef.current = new Audio();
            }
            const audio = audioRef.current;
            audio.src = chunk.audio_url;
            audio.playbackRate = speed;
            audio.load();
        },
        [chunks, speed, onChunkStart, onComplete],
    );

    const tickLoop = useCallback(() => {
        const run = () => {
            const audio = audioRef.current;
            if (!audio || audio.paused) return;

            const elapsed = audio.currentTime * 1000;
            setChunkElapsed(Math.round(elapsed));

            const chunk = chunks[currentChunk];
            if (chunk?.word_timings) {
                const timings = chunk.word_timings;
                let wordIdx = -1;
                for (let i = 0; i < timings.length; i++) {
                    if (elapsed >= timings[i].start_ms) {
                        wordIdx = i;
                    }
                }
                setCurrentWord(wordIdx);
            }
            rafRef.current = requestAnimationFrame(run);
        };
        run();
    }, [chunks, currentChunk]);

    const startPlayback = useCallback(() => {
        const audio = audioRef.current;
        if (!audio) return;

        audio.playbackRate = speed;
        audio
            .play()
            .then(() => {
                setState("playing");
                tickLoop();
            })
            .catch(() => {
                // Autoplay blocked — stay in loading state
                setState("idle");
            });
    }, [speed, tickLoop]);

    const beginFromStart = useCallback(() => {
        setState("loading");
        loadChunk(0);
        setTimeout(startPlayback, 100);
    }, [loadChunk, startPlayback]);
    // ── Audio event handlers ─────────────────────────────────

    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const handleEnded = () => {
            cancelAnimationFrame(rafRef.current);

            // Gap between chunks, then load next
            setTimeout(() => {
                loadChunk(currentChunk + 1);
                // Auto-continue if we were playing
                if (state === "playing") {
                    setTimeout(startPlayback, 50);
                }
            }, gapMs / speed);
        };

        const handleCanPlay = () => {
            if (state === "loading") {
                startPlayback();
            }
        };

        audio.addEventListener("ended", handleEnded);
        audio.addEventListener("canplaythrough", handleCanPlay);

        return () => {
            audio.removeEventListener("ended", handleEnded);
            audio.removeEventListener("canplaythrough", handleCanPlay);
        };
    }, [currentChunk, state, gapMs, speed, loadChunk, startPlayback]);

    // ── Cleanup on unmount ───────────────────────────────────

    useEffect(() => {
        return () => {
            cancelAnimationFrame(rafRef.current);
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current.src = "";
            }
        };
    }, []);

    // ── Initial autoplay bootstrap ───────────────────────────

    useEffect(() => {
        if (state !== "loading") return;
        if (audioRef.current) return;
        if (chunks.length === 0) return;

        const chunk = chunks[0];
        onChunkStart?.(0);
        audioRef.current = new Audio();
        audioRef.current.src = chunk.audio_url;
        audioRef.current.playbackRate = speed;
        audioRef.current.load();

        setTimeout(startPlayback, 100);
    }, [state, chunks, speed, onChunkStart, startPlayback]);

    // ── Speed changes ────────────────────────────────────────

    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.playbackRate = speed;
        }
    }, [speed]);

    // ── Controls ─────────────────────────────────────────────

    const play = useCallback(() => {
        if (state === "ended") {
            // Restart from beginning
            beginFromStart();
        } else if (state === "paused") {
            startPlayback();
        } else if (state === "idle" && chunks.length > 0) {
            beginFromStart();
        }
    }, [state, chunks.length, startPlayback, beginFromStart]);

    const pause = useCallback(() => {
        cancelAnimationFrame(rafRef.current);
        if (audioRef.current) {
            audioRef.current.pause();
        }
        setState("paused");
    }, []);

    const toggle = useCallback(() => {
        if (state === "playing") pause();
        else play();
    }, [state, play, pause]);

    const skipTo = useCallback((index: number) => {
        if (index < 0 || index >= chunks.length) return;
        cancelAnimationFrame(rafRef.current);
    
        // Remember if we were playing before skipping
        const wasPlaying = state === "playing"; 
    
        // Set to loading if we intend to auto-resume
        if (wasPlaying) setState("loading"); 
    
        loadChunk(index);
    }, [chunks.length, state, loadChunk]);
    
    
    
    // ── Context value ────────────────────────────────────────

    const ctx: NarrationContext = {
        state,
        currentChunk,
        currentWord,
        chunkElapsed,
        totalElapsed,
        totalDuration,
        speed,
        play,
        pause,
        toggle,
        skipTo,
        setSpeed,
    };

    return <NarrationCtx.Provider value={ctx}>{children}</NarrationCtx.Provider>;
}
