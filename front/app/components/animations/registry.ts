
import type { ComponentType } from "react";
import type { AnimationTemplateProps } from "./types";
import { FractionBars } from "./FractionBars";
import { NumberLine } from "./NumberLine";
import { BarChart } from "./BarChart";
import { AreaModel } from "./AreaModel";
import { CoordinatePlane } from "./CoordinatePlane";
import { PassageStructure } from "./PassageStructure";
import { CauseEffect } from "./CauseEffect";
import { EquationBalance } from "./EquationBalance";

type TemplateComponent = ComponentType<AnimationTemplateProps<Record<string, unknown>>>;

export const templateRegistry: Record<string, TemplateComponent> = {
    fraction_bars: FractionBars as unknown as TemplateComponent,
    number_line: NumberLine as unknown as TemplateComponent,
    bar_chart: BarChart as unknown as TemplateComponent,
    area_model: AreaModel as unknown as TemplateComponent,
    coordinate_plane: CoordinatePlane as unknown as TemplateComponent,
    passage_structure: PassageStructure as unknown as TemplateComponent,
    cause_effect: CauseEffect as unknown as TemplateComponent,
    equation_balance: EquationBalance as unknown as TemplateComponent,
};
