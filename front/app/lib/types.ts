export interface JobListing {
  id: string;
  title: string;
  company: string;
  location?: string;
  description?: string;
  url?: string;
  salary?: string;
}

export interface Agency {
  id: string;
  name: string;
  description?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  fees?: string;
  espanol?: boolean | string[] | string;
  services?: string[];
  contacts?: string[];
  distance_miles?: number;
}

export type CareerView = 'resume' | 'cover_letter' | 'jobs';

export interface ResourceState {
  // Map Data
  found_agencies: Agency[];
  saved_agencies: Agency[];
  selected_agency_id: string | null;
  
  // Career Data
  resume_markdown: string;
  cover_letter_markdown: string;
  job_listings: JobListing[];
  career_view: CareerView; // Agent changes this to switch tabs
}
