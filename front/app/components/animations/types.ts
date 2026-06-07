export interface AnimationCue {
    step: string;
    trigger_at_chunck: number;
    delay_ms?: number;
    duration_ms?: number;

}

export interface AnimationTemplateProps<P = Record<string, unknown>> {
    props: P;
    activeStep: string;
    speed: number;
    scaffoldLevel: number;
    isPlaying: boolean;
    className?: string;

}

export const SVG_DEFAULTS = {
    width: 480,
    height: 320,
    padding: 40,
} as const;

