"""
upskill/content_team/agents.py

Content Generation Team agents:

  1. LessonDesignerAgent     — Plans the session structure (ZPD-aware sequencing)
  2. AssessmentBuilderAgent  — Generates themed question variations (GLM-4 / cheap + good)
  3. MediaThemeAgent         — Applies learner theme/interest to content + generates assets
  4. ScaffoldingAgent        — Builds 4-level hint progressions for each item
  5. ContentValidatorAgent   — Cross-provider validation (Gemini Pro validates GLM output)

Cross-provider bias removal:
  Generator: GLM-4 (THUDM) — cheap, strong at structured generation, diverse training
  Validator: Gemini 2.0 Flash — different architecture, different RLHF
  Supervisor: Claude Opus — synthesizes, makes final call
"""

from __future__ import annotations
import json
from typing import Optional
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from .schemas import (
    SeedItem,
    GeneratedItem,
    ValidationResult,
    LessonPlan,
    SubjectKey,
    ScaffoldLevel,
    ContentStatus,
)


# ---------------------------------------------------------------------------
# Model selection — cross-provider for bias removal
# ---------------------------------------------------------------------------

def get_generator_model():
    """
    Primary content generator.
    GLM-4 preferred (cheap, diverse training corpus, strong at structured output).
    Falling back to GPT-4o-mini as widely available alternative.
    In production: swap base_url to Zhipu AI endpoint for GLM-4.
    """
    # GLM-4 via OpenAI-compatible endpoint:
    # return ChatOpenAI(
    #     model="glm-4",
    #     base_url="https://open.bigmodel.cn/api/paas/v4/",
    #     api_key=os.environ["ZHIPU_API_KEY"],
    #     temperature=0.7,  # Some creativity for theming
    # )
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


def get_validator_model():
    """
    Cross-provider validator — MUST be different from generator.
    Gemini 2.0 Flash: fast, accurate, different training from GLM/GPT.
    """
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,  # Deterministic validation
    )


def get_supervisor_model():
    """Claude Opus as content supervisor — highest reasoning for final decisions."""
    return ChatAnthropic(model="claude-opus-4-5", temperature=0)


def get_scaffolding_model():
    """Claude Sonnet for scaffolding — strong at pedagogical hint writing."""
    return ChatAnthropic(model="claude-sonnet-4-5", temperature=0.3)


# ---------------------------------------------------------------------------
# Seed DB — DEMO / FALLBACK DATA ONLY
#
# In production, seeds are stored in the `seed_items` Supabase table and
# fetched via `tools_bridge.fetch_seed_content`. GED seeds are already in
# the DB; other curricula will be seeded by content authors.
#
# This dict exists only as a local fallback for development and testing.
# ---------------------------------------------------------------------------

SEED_DB: dict[str, list[SeedItem]] = {
    "math": [
        SeedItem(
            seed_id="seed_math_fractions_001",
            subject="math",
            skill_id="fractions_decimals",
            question_type="multiple_choice",
            difficulty_b=-1.0,
            discrimination_a=1.2,
            question_text="Which list shows 1/2, 0.6, 4/5, 1/8, 0.07 arranged from smallest to largest?",
            choices=[
                "A. 0.07, 1/8, 1/2, 0.6, 4/5",
                "B. 1/2, 4/5, 0.6, 0.07, 1/8",
                "C. 1/8, 1/2, 0.6, 0.07, 4/5",
                "D. 0.07, 1/8, 4/5, 1/2, 0.6",
            ],
            correct_answer="A",
            correct_rationale="Convert all to decimals: 0.5, 0.6, 0.8, 0.125, 0.07. Ordered: 0.07, 0.125, 0.5, 0.6, 0.8",
            distractor_rationales={
                "B": "Learner ordered largest to smallest instead of smallest to largest",
                "C": "Learner confused 0.07 with 0.7, placing it incorrectly",
                "D": "Learner didn't convert fractions before comparing",
            },
            curriculum_standard="MP.1",
            employment_contexts=["reading a pay stub", "comparing discount percentages"],
        ),
        SeedItem(
            seed_id="seed_math_percentages_001",
            subject="math",
            skill_id="percentages",
            question_type="multiple_choice",
            difficulty_b=-0.5,
            discrimination_a=1.4,
            question_text="A worker earns $800 per week. If 15% is withheld for taxes, how much is withheld?",
            choices=["A. $80", "B. $120", "C. $150", "D. $200"],
            correct_answer="B",
            correct_rationale="15% of $800 = 0.15 × 800 = $120",
            distractor_rationales={
                "A": "Calculated 10% instead of 15%",
                "C": "Used $1000 as base instead of $800",
                "D": "Calculated 25% instead of 15%",
            },
            curriculum_standard="MP.2",
            employment_contexts=["understanding paycheck deductions", "calculating take-home pay"],
        ),
        SeedItem(
            seed_id="seed_math_algebra_001",
            subject="math",
            skill_id="basic_algebra",
            question_type="multiple_choice",
            difficulty_b=0.0,
            discrimination_a=1.5,
            question_text="Solve for x: 3x + 7 = 22",
            choices=["A. x = 3", "B. x = 5", "C. x = 7", "D. x = 9"],
            correct_answer="B",
            correct_rationale="Subtract 7 from both sides: 3x = 15. Divide by 3: x = 5",
            distractor_rationales={
                "A": "Subtracted 7 but forgot to divide (3x = 15 → x = 3 error)",
                "C": "Added 7 instead of subtracting",
                "D": "Divided 22 by 3 without subtracting first",
            },
            curriculum_standard="A.CED.1",
            employment_contexts=["calculating hours needed to reach a wage goal", "pricing formulas"],
        ),
    ],
    "science": [
        SeedItem(
            seed_id="seed_sci_experimental_001",
            subject="science",
            skill_id="experimental_design",
            question_type="multiple_choice",
            difficulty_b=-1.5,
            discrimination_a=1.0,
            question_text=(
                "A researcher tests whether pectinase increases apple juice yield. "
                "They add pectinase to Beaker A and water to Beaker B, then measure juice. "
                "What is the dependent variable?"
            ),
            choices=[
                "A. The amount of juice produced",
                "B. The mass of chopped apple",
                "C. The presence of pectinase",
                "D. The time left undisturbed",
            ],
            correct_answer="A",
            correct_rationale=(
                "The dependent variable is what is measured/observed — the juice yield. "
                "Pectinase presence is the independent variable; apple mass and time are controls."
            ),
            distractor_rationales={
                "B": "Apple mass is a controlled variable, kept constant in both beakers",
                "C": "Pectinase is the independent variable (what's being manipulated)",
                "D": "Time is a controlled variable, kept the same for both beakers",
            },
            curriculum_standard="SP.1",
            employment_contexts=["following lab protocols", "quality control procedures"],
        ),
    ],
    "social_studies": [
        SeedItem(
            seed_id="seed_ss_argument_001",
            subject="social_studies",
            skill_id="argument_evidence",
            question_type="multiple_choice",
            difficulty_b=0.5,
            discrimination_a=1.3,
            question_text=(
                "Based on the Manifest Destiny passage: Which statement best shows "
                "Manifest Destiny was used to justify mistreatment of individuals?"
            ),
            choices=[
                "A. 'The new government promoted settlement and expansion west to California.'",
                "B. 'He believed it is a right such as that of the tree to space suitable for growth.'",
                "C. 'Some people have contended this ideology was a form of racism.'",
                "D. 'O'Sullivan argued white Americans had the right to bring democracy to backward peoples by force.'",
            ],
            correct_answer="D",
            correct_rationale=(
                "Choice D explicitly states force was justified against groups O'Sullivan called 'backward' — "
                "direct evidence of justifying mistreatment."
            ),
            distractor_rationales={
                "A": "Describes expansion but doesn't address justifying mistreatment of people",
                "B": "Natural rights metaphor — doesn't directly address mistreatment",
                "C": "Others' opinion about racism, not direct evidence from the text",
            },
            curriculum_standard="RH.2",
            employment_contexts=["evaluating workplace policy arguments", "reading HR documentation"],
        ),
    ],
    "rla": [
        SeedItem(
            seed_id="seed_rla_inference_001",
            subject="rla",
            skill_id="inference",
            question_type="multiple_choice",
            difficulty_b=-0.5,
            discrimination_a=1.3,
            question_text=(
                "In the Anne of Green Gables excerpt, Anne asks Marilla to call her 'Cordelia.' "
                "What does this request most reveal about Anne?"
            ),
            choices=[
                "A. She tried to make her life more interesting.",
                "B. She wishes she could fit in better with her peers.",
                "C. She feels confused about her own past.",
                "D. She hesitates to share personal details.",
            ],
            correct_answer="A",
            correct_rationale=(
                "Anne has always imagined a more elegant name — she says she's 'imagined' it. "
                "This shows she actively creates a richer inner life to compensate for her difficult reality."
            ),
            distractor_rationales={
                "B": "No mention of peers; the situation is about her placement at this home",
                "C": "Anne knows her name and past; she's choosing to imagine a different one",
                "D": "Anne is actually quite open; she freely explains her preference",
            },
            curriculum_standard="RLA.R.2.1",
            employment_contexts=["understanding workplace communication subtext", "reading between the lines in emails"],
        ),
    ],
}


def fetch_seeds_for_skill(subject: SubjectKey, skill_id: str, count: int = 3) -> list[SeedItem]:
    """Fetch seed items from DB for a given skill. Returns up to `count` seeds."""
    subject_seeds = SEED_DB.get(subject, [])
    skill_seeds = [s for s in subject_seeds if s.skill_id == skill_id]
    
    # Fall back to any seed for the subject if skill not found
    if not skill_seeds:
        skill_seeds = subject_seeds
    
    return skill_seeds[:count]


# ---------------------------------------------------------------------------
# Theme engine — applies interests to question context
# ---------------------------------------------------------------------------

THEME_CONTEXTS = {
    "gaming": {
        "math_fractions": "comparing player stats in a video game leaderboard",
        "math_percentages": "calculating XP boost percentages and in-game currency",
        "math_algebra": "solving for the number of levels needed to reach a goal score",
        "science_experimental": "testing which weapon upgrade deals more damage in a controlled experiment",
        "default": "a gaming tournament scenario",
    },
    "sports": {
        "math_fractions": "comparing batting averages and shooting percentages",
        "math_percentages": "calculating player salary deductions and signing bonuses",
        "math_algebra": "figuring out how many points a team needs to make playoffs",
        "science_experimental": "testing whether a new training routine improves sprint times",
        "default": "a sports analytics scenario",
    },
    "space": {
        "math_fractions": "calculating fuel ratios for a spacecraft mission",
        "math_percentages": "computing oxygen consumption rates on a space station",
        "math_algebra": "solving for travel time to reach a distant planet",
        "science_experimental": "testing which heat shield material withstands reentry best",
        "default": "a space exploration mission",
    },
    "nature": {
        "math_fractions": "measuring rainfall amounts across different forest regions",
        "math_percentages": "calculating what percentage of a species population survived",
        "math_algebra": "determining how many days until a river reaches flood level",
        "science_experimental": "testing whether soil type affects plant growth rate",
        "default": "an environmental field study",
    },
    "urban": {
        "math_fractions": "comparing rent costs across different city neighborhoods",
        "math_percentages": "calculating sales tax and discounts at urban businesses",
        "math_algebra": "figuring out a delivery driver's earnings formula",
        "science_experimental": "testing whether different surfaces retain heat differently",
        "default": "an urban community scenario",
    },
}


def get_theme_context(theme: str, subject: str, skill_id: str, freeform: Optional[str] = None) -> str:
    """
    Generate a theme context string for content generation.
    Freeform interests (e.g. "rick and morty") take priority over standard themes.
    """
    if freeform:
        # Micro-theming: embed the specific interest directly
        return f"a {freeform} scenario — use characters, settings, or concepts from {freeform}"
    
    theme_map = THEME_CONTEXTS.get(theme, THEME_CONTEXTS["gaming"])
    key = f"{subject}_{skill_id.split('_')[0]}"
    return theme_map.get(key, theme_map.get("default", f"a {theme} scenario"))


# ---------------------------------------------------------------------------
# 1. LessonDesignerAgent
# ---------------------------------------------------------------------------

def build_lesson_designer():
    """
    Plans the session: what items go in warmup, instruction, practice, generalization.
    Uses ZPD principles — warmup at mastered level, practice at target theta ± 0.5.
    """
    model = get_generator_model()

    @tool
    def design_lesson_sequence(
        learner_id: str,
        subject: str,
        target_skill_id: str,
        target_theta: float,
        mastered_skills: str,
        session_number: int = 1,
    ) -> str:
        """
        Create a lesson plan structure for this session.
        Returns JSON lesson plan with item slot specifications.
        """
        mastered = json.loads(mastered_skills) if mastered_skills else []
        
        # ZPD: target items should be at theta ± 0.5
        zpd_min = target_theta - 0.3
        zpd_max = target_theta + 0.5
        
        # Behavioral momentum: warmup uses mastered skills (easy wins)
        warmup_skill = mastered[-1] if mastered else target_skill_id
        
        plan = {
            "plan_structure": {
                "warmup": {
                    "skill_id": warmup_skill,
                    "count": 2,
                    "difficulty_range": [target_theta - 1.5, target_theta - 0.8],
                    "purpose": "Build momentum with familiar content before new material",
                },
                "instruction": {
                    "skill_id": target_skill_id,
                    "count": 2,
                    "difficulty_range": [zpd_min, target_theta],
                    "purpose": "Introduce target skill at accessible difficulty",
                    "include_worked_example": True,
                },
                "practice": {
                    "skill_id": target_skill_id,
                    "count": 3,
                    "difficulty_range": [target_theta, zpd_max],
                    "purpose": "Apply skill at optimal challenge level (70-80% success target)",
                },
                "generalization": {
                    "skill_id": target_skill_id,
                    "count": 1,
                    "difficulty_range": [target_theta - 0.2, target_theta + 0.2],
                    "purpose": "Transfer to employment context",
                    "employment_bridge": True,
                },
            },
            "total_items": 8,
            "estimated_minutes": 20 + (session_number * 2),  # Sessions get slightly longer
            "target_theta": target_theta,
            "zpd_range": [zpd_min, zpd_max],
        }
        
        return json.dumps(plan)

    @tool
    def select_seed_for_slot(
        subject: str,
        skill_id: str,
        slot_type: str,
        difficulty_min: float,
        difficulty_max: float,
    ) -> str:
        """
        Select the best seed item for a given lesson slot.
        Returns seed metadata to guide content generation.
        """
        seeds = fetch_seeds_for_skill(subject, skill_id)  # type: ignore
        
        # Find seeds in difficulty range
        matching = [
            s for s in seeds
            if difficulty_min <= s.difficulty_b <= difficulty_max
        ]
        
        # Fall back to closest if none in range
        if not matching and seeds:
            matching = sorted(seeds, key=lambda s: abs(s.difficulty_b - (difficulty_min + difficulty_max) / 2))
        
        if not matching:
            return json.dumps({"error": f"No seeds found for {skill_id}"})
        
        seed = matching[0]
        return json.dumps({
            "seed_id": seed.seed_id,
            "skill_id": seed.skill_id,
            "difficulty_b": seed.difficulty_b,
            "discrimination_a": seed.discrimination_a,
            "question_type": seed.question_type,
            "curriculum_standard": seed.curriculum_standard,
            "employment_contexts": seed.employment_contexts,
            "slot_type": slot_type,
        })

    agent = create_agent(
        model=model,
        tools=[design_lesson_sequence, select_seed_for_slot],
        system_prompt="""You are the Lesson Designer Agent for UpSkill.

You plan learning sessions using Zone of Proximal Development (ZPD) principles.

Key principles:
- Warmup items should be EASY (mastered content) to build behavioral momentum
- Core instruction starts slightly below target theta, rises to target
- Practice items challenge at 70-80% expected success rate  
- Generalization always connects to employment context
- Sessions run 20-30 minutes (adult learners with limited time)

Always call design_lesson_sequence first, then select_seed_for_slot for each slot.

Return a complete lesson plan JSON with seed assignments for each slot.
""",
        name="lesson_designer_agent",
    )
    return agent


# ---------------------------------------------------------------------------
# 2. AssessmentBuilderAgent (Generator — GLM-4 / GPT-4o-mini)
# ---------------------------------------------------------------------------

def build_assessment_builder():
    """
    Generates themed question variations from seed items.
    This is the primary content generator — uses the cheaper/diverse model.
    
    KEY: Generated content always references the seed for structure.
    The theme changes the CONTEXT, never the underlying skill or difficulty.
    """
    model = get_generator_model()

    @tool
    def generate_themed_variation(
        seed_json: str,
        theme_context: str,
        freeform_interest: str = "",
        employment_bridge: str = "",
        learning_style: str = "visual",
    ) -> str:
        """
        Generate a themed variation of a seed item.
        
        The theme wraps the math/science/SS/RLA in an engaging context
        WITHOUT changing the underlying cognitive demand or difficulty.
        
        Returns generated item JSON.
        """
        # This tool is called by the agent, which then uses the LLM to generate
        # The tool itself structures the generation request
        seed = json.loads(seed_json)
        
        generation_prompt = {
            "task": "generate_themed_question",
            "seed_skill": seed.get("skill_id"),
            "seed_difficulty": seed.get("difficulty_b"),
            "seed_question": seed.get("question_text"),
            "seed_choices": seed.get("choices"),
            "seed_answer": seed.get("correct_answer"),
            "seed_rationale": seed.get("correct_rationale"),
            "distractor_rationales": seed.get("distractor_rationales", {}),
            "theme_context": theme_context,
            "freeform_interest": freeform_interest,
            "employment_bridge": employment_bridge,
            "learning_style": learning_style,
            "instructions": (
                "Rewrite the question using the theme context. "
                "The math/logic must remain IDENTICAL — same operations, same numbers (or proportionally equivalent), "
                "same cognitive demand. Only the STORY WRAPPER changes. "
                "Preserve all four answer choices with the same distractors representing the same misconceptions. "
                "Write an employment_bridge sentence connecting this skill to real work."
            ),
        }
        
        return json.dumps(generation_prompt)

    @tool
    def validate_theme_coherence(
        original_seed_json: str,
        generated_item_json: str,
    ) -> str:
        """
        Quick self-check before sending to external validator.
        Verifies the generated item didn't accidentally change the math/answer.
        """
        try:
            seed = json.loads(original_seed_json)
            generated = json.loads(generated_item_json)
            
            issues = []
            
            # Check answer preserved
            if generated.get("correct_answer") != seed.get("correct_answer"):
                issues.append(f"Answer changed: {seed['correct_answer']} → {generated.get('correct_answer')}")
            
            # Check choice count preserved
            if len(generated.get("choices", [])) != len(seed.get("choices", [])):
                issues.append(f"Choice count changed: {len(seed['choices'])} → {len(generated.get('choices', []))}")
            
            # Check question isn't too long (readability)
            q_len = len(generated.get("question_text", ""))
            if q_len > 500:
                issues.append(f"Question too long ({q_len} chars) — risk of cognitive overload")
            
            return json.dumps({
                "self_check_passed": len(issues) == 0,
                "issues": issues,
            })
        except Exception as e:
            return json.dumps({"self_check_passed": False, "issues": [str(e)]})

    agent = create_agent(
        model=model,
        tools=[generate_themed_variation, validate_theme_coherence],
        system_prompt="""You are the Assessment Builder Agent for UpSkill.

Your job: generate themed variations of canonical seed questions.

The seed item is AUTHORITATIVE. You are rewriting the wrapper, not the content.

Rules:
1. PRESERVE: The mathematical/logical operation, the numbers, the correct answer, 
   the distractor logic (what misconception each wrong answer tests)
2. CHANGE: The story context, names, settings, objects — wrap in the learner's theme
3. EMPLOYMENT BRIDGE: Always add one sentence connecting the skill to real workplace use
4. LEARNING STYLE: If visual → add description of a diagram. If auditory → write as 
   if explaining verbally. If kinesthetic → make it an action/process.

For a gaming-themed fraction question:
SEED: "Which list shows 1/2, 0.6, 4/5, 1/8, 0.07 from smallest to largest?"
THEMED: "In a battle royale game, four players have these accuracy rates: 
1/2, 0.6, 4/5, 1/8, 0.07. Which list ranks them from lowest to highest accuracy?"

Same math. Same answer. Same distractors. Different world.

Use generate_themed_variation to structure the generation, then produce the actual
themed question text. Run validate_theme_coherence before returning.

Return complete GeneratedItem JSON.
""",
        name="assessment_builder_agent",
    )
    return agent


# ---------------------------------------------------------------------------
# 3. MediaThemeAgent
# ---------------------------------------------------------------------------

def build_media_theme_agent():
    """
    Applies the learner's specific theme and freeform interests to content.
    Also generates asset descriptions for visual/audio content.
    """
    model = get_generator_model()

    @tool
    def apply_freeform_interest(
        question_text: str,
        freeform_interest: str,
        subject: str,
        skill_id: str,
    ) -> str:
        """
        Apply a specific freeform interest (e.g. 'Rick and Morty', 'Hello Kitty')
        to a question. More precise than generic theming.
        """
        application_guide = {
            "rick and morty": {
                "math": "Use Rick's portal gun experiments, Morty's grades, or interdimensional currencies",
                "science": "Frame as Rick's lab experiments — he'd use proper controls and variables",
                "social_studies": "Use the Citadel of Ricks as a governmental structure analogy",
                "rla": "Use a passage about an eccentric genius and his reluctant companion",
            },
            "hello kitty": {
                "math": "Use Sanrio merchandise pricing, ribbon measurements, star collection counts",
                "science": "Frame as experiments in a Sanrio laboratory with cute but rigorous methods",
                "social_studies": "Use Sanrio's global popularity as an economics/cultural exchange example",
                "rla": "Use a story about a character finding their place in a new community",
            },
            "minecraft": {
                "math": "Use block counting, crafting ratios, resource calculations, and coordinates",
                "science": "Frame as testing different farm designs or potion brewing experiments",
                "social_studies": "Use a Minecraft server economy as supply/demand example",
                "rla": "Use a passage about building, exploration, and creativity",
            },
            "naruto": {
                "math": "Use chakra percentages, ninja ranks, training time calculations",
                "science": "Frame as testing jutsu effectiveness with controlled trials",
                "social_studies": "Use the hidden village system as a governance structure",
                "rla": "Use a passage about perseverance and finding one's path",
            },
        }
        
        # Find matching interest (fuzzy)
        interest_lower = freeform_interest.lower()
        guide = None
        for key, val in application_guide.items():
            if key in interest_lower or interest_lower in key:
                guide = val.get(subject, f"a {freeform_interest} scenario")
                break
        
        if not guide:
            guide = f"a {freeform_interest} scenario relevant to {skill_id}"
        
        return json.dumps({
            "freeform_interest": freeform_interest,
            "application_context": guide,
            "instruction": f"Rewrite this question using: {guide}. Question: {question_text}",
        })

    @tool
    def generate_visual_asset_description(
        question_text: str,
        skill_id: str,
        theme: str,
    ) -> str:
        """
        Generate a description of a visual asset to accompany the question.
        For visual learners — the asset description gets sent to image generation
        or a diagram renderer.
        """
        visual_templates = {
            "fractions_decimals": f"A number line from 0 to 1 with tick marks, themed as {theme} (e.g. a score meter)",
            "percentages": f"A pie chart or bar graph showing percentage breakdown, styled in {theme} aesthetic",
            "basic_algebra": f"A balance scale with algebraic expressions, decorated with {theme} imagery",
            "linear_equations": f"A coordinate grid with a plotted line, axis labels using {theme} vocabulary",
            "experimental_design": f"A side-by-side diagram of two experimental setups, labeled A and B, {theme} styled",
            "inference": f"A split panel showing text passage on left, comprehension question on right",
            "argument_evidence": f"A diagram showing claim → evidence → warrant chain",
        }
        
        description = visual_templates.get(
            skill_id,
            f"A clear, {theme}-themed illustration supporting the question concept"
        )
        
        return json.dumps({
            "asset_type": "diagram",
            "description": description,
            "accessibility_alt_text": f"Visual aid for {skill_id} question",
            "render_priority": "high" if skill_id in ["experimental_design", "linear_equations"] else "medium",
        })

    @tool
    def generate_audio_script(
        question_text: str,
        correct_rationale: str,
        tone: str = "encouraging",
    ) -> str:
        """
        Generate a read-aloud audio script for auditory learners.
        Includes the question, thinking prompts, and explanation.
        """
        tone_styles = {
            "encouraging": "warm, supportive, uses 'you've got this' and 'great thinking'",
            "casual": "conversational, uses contractions, like a knowledgeable friend",
            "direct": "clear and concise, no filler words, just the facts",
            "humorous": "light humor, uses analogies, makes the content fun",
        }
        
        style = tone_styles.get(tone, tone_styles["encouraging"])
        
        script = {
            "intro": f"[Read in {style} voice]",
            "question_read": question_text,
            "think_prompt": "Take a moment to think it through before selecting your answer...",
            "after_correct": f"Exactly right! {correct_rationale}",
            "after_incorrect": "Not quite — let's think about this differently...",
            "explanation": correct_rationale,
        }
        
        return json.dumps(script)

    agent = create_agent(
        model=model,
        tools=[apply_freeform_interest, generate_visual_asset_description, generate_audio_script],
        system_prompt="""You are the Media & Theme Agent for UpSkill.

Your job is to apply the learner's specific interests and modality preferences
to content, and generate asset descriptions for visual/audio support.

Priority order for theming:
1. FREEFORM INTERESTS first (e.g. "Hello Kitty", "Rick and Morty") — most specific
2. PRIMARY THEME second (gaming, sports, space, etc.) — fallback
3. Generic educational — last resort only

For visual learners: always generate a visual_asset_description
For auditory learners: always generate an audio_script
For kinesthetic: note in the question that an interactive element should be added

Return JSON with all applied assets and the final themed question.
""",
        name="media_theme_agent",
    )
    return agent


# ---------------------------------------------------------------------------
# 4. ScaffoldingAgent
# ---------------------------------------------------------------------------

def build_scaffolding_agent():
    """
    Generates 4-level hint progressions for each content item.
    Each level adds more support without revealing the answer.
    
    Level 1: General strategy (what approach to use)
    Level 2: Specific direction (what to do first)
    Level 3: Worked example (similar problem solved)
    Level 4: Step-by-step guide (decomposed for this exact problem)
    """
    model = get_scaffolding_model()

    @tool
    def generate_hint_progression(
        question_text: str,
        skill_id: str,
        correct_answer: str,
        correct_rationale: str,
        choices: str,
    ) -> str:
        """
        Generate 4 progressive hints for a question.
        Each hint increases specificity WITHOUT giving away the answer.
        """
        choices_list = json.loads(choices) if choices else []
        
        # Template-based scaffolding per skill type (LLM enriches these)
        skill_strategies = {
            "fractions_decimals": {
                "strategy": "Converting everything to the same format (all decimals or all fractions) makes comparison easy.",
                "direction": "Start by converting each fraction to a decimal by dividing the top number by the bottom.",
                "example": "For example: 3/4 = 3 ÷ 4 = 0.75. Now you can compare 0.75 to other decimals directly.",
                "step_by_step": "Step 1: Write each number. Step 2: Convert fractions to decimals. Step 3: Line them up by decimal place. Step 4: Order from smallest to largest.",
            },
            "percentages": {
                "strategy": "Percent means 'per hundred.' To find a percent of a number, multiply by the decimal version.",
                "direction": "Convert the percentage to a decimal first by dividing by 100 (15% → 0.15).",
                "example": "Example: 10% of $800 = 0.10 × 800 = $80. So 15% would be a bit more than that.",
                "step_by_step": "Step 1: Write the percent. Step 2: Divide by 100 to get decimal. Step 3: Multiply by the base amount. Step 4: Check your answer makes sense.",
            },
            "basic_algebra": {
                "strategy": "To solve for x, get x alone on one side by doing the same operation to both sides.",
                "direction": "Look at what's being added or subtracted from x. Do the opposite to both sides first.",
                "example": "Example: If x + 3 = 10, subtract 3 from both sides: x = 7.",
                "step_by_step": "Step 1: Identify what's added/subtracted (undo it first). Step 2: Then undo multiplication/division. Step 3: Check by substituting back.",
            },
            "experimental_design": {
                "strategy": "In any experiment, ask: What am I CHANGING? What am I MEASURING? What stays the SAME?",
                "direction": "The dependent variable is always what you MEASURE at the end of the experiment.",
                "example": "Example: Testing if watering plants more makes them taller — you measure HEIGHT (dependent), you change WATER AMOUNT (independent).",
                "step_by_step": "Step 1: Find what the researcher DID differently (independent). Step 2: Find what was MEASURED or OBSERVED (dependent). Step 3: Find what was kept the SAME (controlled).",
            },
            "inference": {
                "strategy": "An inference is a conclusion you draw from clues in the text — it's not stated directly.",
                "direction": "Look at what the character DOES and SAYS. Ask: what does this tell us about who they are?",
                "example": "Example: If someone keeps practicing violin even after failing, you can infer they're determined — even if the text never says 'determined.'",
                "step_by_step": "Step 1: Find the specific behavior or quote. Step 2: Ask what this behavior suggests. Step 3: Pick the answer that fits the EVIDENCE, not just what seems nice.",
            },
            "argument_evidence": {
                "strategy": "Strong evidence DIRECTLY supports the claim — it doesn't just relate to the topic.",
                "direction": "For each choice, ask: Does this actually PROVE the specific point being made?",
                "example": "Example: If the claim is 'the policy hurt workers,' evidence about policy creation doesn't prove it — you need evidence of workers being hurt.",
                "step_by_step": "Step 1: Identify the exact claim being made. Step 2: For each choice, ask 'does this directly prove the claim?' Step 3: Eliminate choices that are only related, not proving.",
            },
        }
        
        defaults = skill_strategies.get(skill_id, {
            "strategy": "Break this problem into smaller steps and tackle each one.",
            "direction": "Read the question carefully and identify what information you're given.",
            "example": "Think about a simpler version of this problem first.",
            "step_by_step": "Step 1: Identify what you know. Step 2: Identify what you need to find. Step 3: Choose your approach. Step 4: Check your work.",
        })
        
        return json.dumps({
            "general_strategy": defaults["strategy"],
            "specific_direction": defaults["direction"],
            "worked_example": defaults["example"],
            "step_by_step": defaults["step_by_step"],
        })

    @tool
    def generate_error_specific_feedback(
        question_text: str,
        distractor_rationales: str,
        correct_answer: str,
    ) -> str:
        """
        Generate targeted feedback for each wrong answer.
        When a learner picks a distractor, they get feedback specific to
        the misconception that answer represents.
        """
        rationales = json.loads(distractor_rationales) if distractor_rationales else {}
        
        feedback = {}
        for choice, misconception in rationales.items():
            feedback[choice] = {
                "immediate_feedback": f"That's a common mix-up! {misconception}",
                "redirect": "Let's look at this differently...",
                "hint_to_show": "specific_direction",  # Jump to level 2 hint after error
            }
        
        return json.dumps({"error_feedback": feedback})

    agent = create_agent(
        model=model,
        tools=[generate_hint_progression, generate_error_specific_feedback],
        system_prompt="""You are the Scaffolding Agent for UpSkill.

You create the hint system that supports learners when they struggle.
Your hints must be pedagogically precise — each level adds MORE support
without GIVING AWAY the answer.

Critical rules:
- Level 1 (general_strategy): What TYPE of thinking to use. Never mention the specific numbers.
- Level 2 (specific_direction): What to do FIRST. Still no answer.
- Level 3 (worked_example): Show a SIMILAR but DIFFERENT problem solved. Not this exact one.
- Level 4 (step_by_step): Walk through THIS problem step by step, stopping just before the final answer.

For error feedback: each wrong answer represents a specific misconception.
Your feedback names and corrects that misconception warmly.

Always generate both hint progressions AND error feedback.
Return complete scaffolding JSON.
""",
        name="scaffolding_agent",
    )
    return agent


# ---------------------------------------------------------------------------
# 5. ContentValidatorAgent (Cross-provider — Gemini validates GLM/GPT output)
# ---------------------------------------------------------------------------

def build_content_validator():
    """
    Cross-provider content validator.
    
    Generator: GPT-4o-mini / GLM-4
    Validator: Gemini 2.0 Flash (different provider — removes self-consistency bias)
    
    This is the quality gate. Nothing reaches the learner without passing here.
    """
    model = get_validator_model()

    @tool
    def validate_math_accuracy(
        question_text: str,
        choices: str,
        correct_answer: str,
        correct_rationale: str,
        skill_id: str,
    ) -> str:
        """
        Verify mathematical accuracy of a generated question.
        Works through the problem independently and checks the answer.
        
        This is the most critical validation for Math and Science.
        """
        choices_list = json.loads(choices) if choices else []
        
        # The validator LLM will actually solve this problem
        # Here we structure what to check
        validation_request = {
            "task": "verify_math_problem",
            "question": question_text,
            "choices": choices_list,
            "claimed_answer": correct_answer,
            "claimed_rationale": correct_rationale,
            "instructions": (
                "1. Solve this problem independently WITHOUT looking at the choices first. "
                "2. Then check which choice matches your answer. "
                "3. Verify the rationale is correct and complete. "
                "4. Check each distractor — does it represent a plausible error? "
                "5. Report any mathematical errors found."
            ),
        }
        
        return json.dumps(validation_request)

    @tool
    def validate_content_quality(
        question_text: str,
        choices: str,
        theme_applied: str,
        seed_skill_id: str,
        employment_bridge: str = "",
        learning_style: str = "visual",
    ) -> str:
        """
        Validate content quality beyond math accuracy:
        - Does the theme make sense without being forced?
        - Is the employment bridge factually accurate?
        - Is the reading level appropriate for adult learners?
        - Does the question still test the intended curriculum skill?
        """
        quality_checklist = {
            "check_theme_naturalness": f"Does the {theme_applied} theme flow naturally or feel forced?",
            "check_reading_level": "Is the question readable for adult learners (Grade 8-10 prose complexity)?",
            "check_answer_unambiguity": "Is there ONE clearly correct answer?",
            "check_distractor_plausibility": "Do wrong answers represent real mistakes, not obvious nonsense?",
            "check_employment_accuracy": f"Is '{employment_bridge}' an accurate real-world application?",
            "check_curriculum_alignment": f"Does this still test {seed_skill_id} as defined in the target curriculum standards?",
        }
        
        return json.dumps({
            "quality_checks": quality_checklist,
            "theme": theme_applied,
            "skill": seed_skill_id,
        })

    @tool
    def produce_validation_verdict(
        item_id: str,
        math_check_result: str,
        quality_check_result: str,
    ) -> str:
        """
        Produce final validation verdict.
        Combines math accuracy + content quality into approved/rejected decision.
        """
        try:
            math_result = json.loads(math_check_result) if math_check_result else {}
            quality_result = json.loads(quality_check_result) if quality_check_result else {}
            
            errors = math_result.get("errors", []) + quality_result.get("errors", [])
            warnings = math_result.get("warnings", []) + quality_result.get("warnings", [])
            
            approved = len(errors) == 0
            confidence = 1.0 - (len(errors) * 0.3) - (len(warnings) * 0.1)
            confidence = max(0.0, min(1.0, confidence))
            
            return json.dumps({
                "item_id": item_id,
                "approved": approved,
                "confidence_score": confidence,
                "rejection_reasons": errors,
                "improvement_suggestions": warnings,
                "validator_model": "gemini-2.0-flash",
            })
        except Exception as e:
            return json.dumps({
                "item_id": item_id,
                "approved": False,
                "confidence_score": 0.0,
                "rejection_reasons": [f"Validation error: {str(e)}"],
                "improvement_suggestions": [],
            })

    agent = create_agent(
        model=model,
        tools=[validate_math_accuracy, validate_content_quality, produce_validation_verdict],
        system_prompt="""You are the Content Validator for UpSkill.

You are the quality gate between content generation and delivery to learners.
Your validation is critical because curriculum preparation is high-stakes.

You were chosen SPECIFICALLY because you are a DIFFERENT AI system than the one
that generated this content. Your job is to catch errors the generator may have
made or rationalized away.

Validation protocol:
1. Call validate_math_accuracy — work through the problem YOURSELF before checking
2. Call validate_content_quality — check all quality dimensions
3. Call produce_validation_verdict — combine results into final decision

Be strict about:
- Mathematical errors (reject immediately)
- Ambiguous answers (reject — learner can't know which is "right")
- Factually wrong employment bridges (reject — teaches bad information)

Be lenient about:
- Minor wording awkwardness (suggest improvement, don't reject)
- Slightly forced theming (warn, don't reject unless it obscures the question)

Your confidence_score determines if the item is cached for other learners:
- > 0.85: Cache for reuse
- 0.7-0.85: Deliver but don't cache
- < 0.7: Reject and regenerate
""",
        name="content_validator_agent",
    )
    return agent
