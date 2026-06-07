-- Praxis Database Schema Generalization Migration
-- 
-- Run this script in your Supabase SQL editor to add `curriculum_id` scoping
-- to the core tables. This enables the platform to host multiple curricula
-- (e.g., GED, CompTIA, TEFL) simultaneously.

-- 1. Add curriculum_id to Learner Profiles
-- (Default to 'ged' to preserve existing user data)
ALTER TABLE public.learner_profiles
ADD COLUMN IF NOT EXISTS curriculum_id text DEFAULT 'ged' NOT NULL;

-- 2. Add curriculum_id to Mastery Records
ALTER TABLE public.learner_mastery
ADD COLUMN IF NOT EXISTS curriculum_id text DEFAULT 'ged' NOT NULL;

-- 3. Add curriculum_id to the Item/Seed Bank
-- This scopes content so GED learners don't get CompTIA questions
ALTER TABLE public.seed_items
ADD COLUMN IF NOT EXISTS curriculum_id text DEFAULT 'ged' NOT NULL;

-- 4. Add curriculum_id to Generated Content Cache
ALTER TABLE public.content_cache
ADD COLUMN IF NOT EXISTS curriculum_id text DEFAULT 'ged' NOT NULL;

-- 5. Add curriculum_id to Skill Chains/Graph
ALTER TABLE public.skill_chains
ADD COLUMN IF NOT EXISTS curriculum_id text DEFAULT 'ged' NOT NULL;

ALTER TABLE public.skill_prerequisites
ADD COLUMN IF NOT EXISTS curriculum_id text DEFAULT 'ged' NOT NULL;

-- Update indexes for faster querying by curriculum
CREATE INDEX IF NOT EXISTS idx_learner_profiles_curriculum ON public.learner_profiles(curriculum_id);
CREATE INDEX IF NOT EXISTS idx_seed_items_curriculum_subject ON public.seed_items(curriculum_id, subject);
CREATE INDEX IF NOT EXISTS idx_content_cache_curriculum ON public.content_cache(curriculum_id);
CREATE INDEX IF NOT EXISTS idx_skill_chains_curriculum ON public.skill_chains(curriculum_id);
