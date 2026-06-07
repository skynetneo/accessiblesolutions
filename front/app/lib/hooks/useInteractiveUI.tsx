"use client";

import { useCopilotAction, useCopilotChatHeadless_c } from "@copilotkit/react-core";
import { MultipleChoice } from "@/components/MultipleChoice";
import { FillInBlank } from "@/components/FillInBlank";
import { DragSort } from "@/components/DragSort";
import { MatchPairs } from "@/components/MatchPairs";
import { TextInput } from "@/components/TextInput";
import { templateRegistry } from "@/components/animations/registry";
import { NarrationStage } from "@/components/narration/NarrationStage";

interface FillBlankArg {
  id: string;
  correctAnswer: string;
  hint?: string;
}

interface DragSortItemArg {
  id: string;
  label: string;
}

interface MatchPairArg {
  id: string;
  left: string;
  right: string;
}

function asNonEmptyString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => asNonEmptyString(item))
    .filter((item) => item.length > 0);
}

function toFillBlankArgs(value: unknown): FillBlankArg[] {
  if (!Array.isArray(value)) return [];
  const blanks: FillBlankArg[] = [];
  for (const item of value) {
    if (!isRecord(item)) continue;
    const id = asNonEmptyString(item.id);
    const correctAnswer = asNonEmptyString(item.correctAnswer);
    const hint = asNonEmptyString(item.hint) || undefined;
    if (!id || !correctAnswer) continue;
    blanks.push({ id, correctAnswer, hint });
  }
  return blanks;
}

function toDragSortItems(value: unknown): DragSortItemArg[] {
  if (!Array.isArray(value)) return [];
  const items: DragSortItemArg[] = [];
  for (const item of value) {
    if (!isRecord(item)) continue;
    const id = asNonEmptyString(item.id);
    const label = asNonEmptyString(item.label);
    if (!id || !label) continue;
    items.push({ id, label });
  }
  return items;
}

function toMatchPairs(value: unknown): MatchPairArg[] {
  if (!Array.isArray(value)) return [];
  const pairs: MatchPairArg[] = [];
  for (const item of value) {
    if (!isRecord(item)) continue;
    const id = asNonEmptyString(item.id);
    const left = asNonEmptyString(item.left);
    const right = asNonEmptyString(item.right);
    if (!id || !left || !right) continue;
    pairs.push({ id, left, right });
  }
  return pairs;
}

function toPropsRecord(value: object | undefined): Record<string, unknown> {
  return value ? { ...value } : {};
}

export function useInteractiveUI() {
  const { sendMessage } = useCopilotChatHeadless_c();

  const sendUserText = async (text: string) => {
    await sendMessage({
      id: crypto.randomUUID(),
      role: "user",
      content: [{ type: "text", text }],
    });
  };

  useCopilotAction({
    name: "present_multiple_choice",
    available: "disabled",
    description: "Presents a multiple choice question to the user",
    parameters: [
      { name: "question", type: "string" },
      { name: "choices", type: "string[]" },
      { name: "correct_answer", type: "string" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
      { name: "prompt_level", type: "number" },
    ],
    render: ({ args, status }) => {
      const question = asNonEmptyString(args.question);
      const choices = toStringArray(args.choices);
      if (!question || choices.length === 0) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading question...
          </div>
        );
      }

      return (
        <div className="my-4">
          <MultipleChoice
            question={question}
            choices={choices}
            disabled={status === "complete"}
            onAnswer={async (choice) => {
              await sendUserText(
                `I selected choice: ${choice}`
              );
            }}
          />
        </div>
      );
    },
  });

  useCopilotAction({
    name: "present_fill_in_blank",
    available: "disabled",
    description: "Presents a fill-in-the-blank question",
    parameters: [
      { name: "template", type: "string" },
      { name: "blanks", type: "object[]" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
      { name: "prompt_level", type: "number" },
    ],
    render: ({ args, status }) => {
      const template = asNonEmptyString(args.template);
      const blanks = toFillBlankArgs(args.blanks);
      if (!template || blanks.length === 0) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading question...
          </div>
        );
      }

      return (
        <div className="my-4">
          <FillInBlank
            template={template}
            blanks={blanks}
            disabled={status === "complete"}
            onSubmit={async (answers) => {
              await sendUserText(
                `My answers for the blanks are: ${JSON.stringify(answers)}`
              );
            }}
          />
        </div>
      );
    },
  });

  useCopilotAction({
    name: "present_drag_sort",
    available: "disabled",
    description: "Presents a drag-and-drop sorting challenge",
    parameters: [
      { name: "instruction", type: "string" },
      { name: "items", type: "object[]" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
      { name: "prompt_level", type: "number" },
    ],
    render: ({ args, status }) => {
      const instruction = asNonEmptyString(args.instruction);
      const items = toDragSortItems(args.items);
      if (!instruction || items.length === 0) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading sorting challenge...
          </div>
        );
      }

      return (
        <div className="my-4">
          <DragSort
            instruction={instruction}
            items={items}
            disabled={status === "complete"}
            onSubmit={async (orderedIds) => {
              await sendUserText(
                `I submitted the following order: ${JSON.stringify(orderedIds)}`
              );
            }}
          />
        </div>
      );
    },
  });

  useCopilotAction({
    name: "present_match_pairs",
    available: "disabled",
    description: "Presents a matching challenge",
    parameters: [
      { name: "instruction", type: "string" },
      { name: "pairs", type: "object[]" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
      { name: "prompt_level", type: "number" },
    ],
    render: ({ args, status }) => {
      const instruction = asNonEmptyString(args.instruction);
      const pairs = toMatchPairs(args.pairs);
      if (!instruction || pairs.length === 0) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading matching challenge...
          </div>
        );
      }

      return (
        <div className="my-4">
          <MatchPairs
            instruction={instruction}
            pairs={pairs}
            disabled={status === "complete"}
            onSubmit={async (matches) => {
              await sendUserText(
                `I submitted the following matches: ${JSON.stringify(matches)}`
              );
            }}
          />
        </div>
      );
    },
  });

  useCopilotAction({
    name: "present_text_response",
    available: "disabled",
    description: "Presents a text input field for the user to type their answer.",
    parameters: [
      { name: "prompt", type: "string" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
      { name: "prompt_level", type: "number" },
    ],
    render: ({ args, status }) => {
      const prompt = asNonEmptyString(args.prompt);
      if (!prompt) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading question...
          </div>
        );
      }

      return (
        <div className="my-4">
          <TextInput
            prompt={prompt}
            disabled={status === "complete"}
            onSubmit={async (answer) => {
              await sendUserText(`My answer is: ${answer}`);
            }}
          />
        </div>
      );
    },
  });

  useCopilotAction({
    name: "present_visual_animation",
    available: "disabled",
    description: "Presents a visual animation or interactive model to the user",
    parameters: [
      { name: "animation_id", type: "string" },
      { name: "props", type: "object" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
    ],
    render: ({ args }) => {
      const animationId = asNonEmptyString(args.animation_id);
      if (!animationId) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading visual animation...
          </div>
        );
      }

      const AnimationComponent = templateRegistry[animationId];
      if (!AnimationComponent) {
        return (
          <div className="text-red-500 glass p-4 rounded-xl">
            Animation {animationId} not found.
          </div>
        );
      }

      return (
        <div className="my-4">
          <AnimationComponent
            props={toPropsRecord(args.props)}
            activeStep="show_grid"
            speed={1.0}
            scaffoldLevel={3}
            isPlaying={true}
          />
        </div>
      );
    },
  });

  useCopilotAction({
    name: "present_audio_narration",
    available: "disabled",
    description: "Presents narrated audio segments to the user.",
    parameters: [
      { name: "text_segments", type: "string[]" },
      { name: "skill_id", type: "string" },
      { name: "chain_step", type: "number" },
    ],
    render: ({ args }) => {
      const textSegments = toStringArray(args.text_segments);
      if (textSegments.length === 0) {
        return (
          <div className="animate-pulse glass p-4 rounded-xl">
            Loading narration...
          </div>
        );
      }

      // Convert the text segments into the chunk format NarrationStage expects
      const chunks = textSegments.map((text: string, i: number) => ({
        content_hash: `hash-${i}`,
        audio_url: "", // In a full prod setup, this would be an actual audio URL
        text: text,
        duration_ms: text.length * 60, // Estimate based on text length
        word_timings: [] // Simulated timings
      }));

      return (
        <div className="my-4">
          <NarrationStage chunks={chunks} autoPlay={false} />
        </div>
      );
    },
  });
}
