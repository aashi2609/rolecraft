/**
 * Cross-domain resume tailoring: map a candidate profile to a target vertical
 * by identifying relevant history, then producing a tailored resume emphasis.
 * Frontend mock — no real LLM call.
 */

export interface CandidateProfile {
  name?: string;
  education?: Array<{ degree?: string; field?: string; school?: string; highlights?: string[] }>;
  experience?: Array<{ title?: string; company?: string; description?: string; skills?: string[] }>;
  skills?: string[];
  projects?: Array<{ name?: string; description?: string; tags?: string[] }>;
  certifications?: Array<{ name?: string; issuer?: string }>;
}

export interface TailoredResume {
  vertical: string;
  score: number;
  date: string;
  emphasis: string[];
  deEmphasized: string[];
  summary: string;
  highlightedSkills: string[];
  highlightedExperience: string[];
  highlightedEducation: string[];
  mappingNotes: string;
}

type VerticalBucket =
  | 'electronics'
  | 'software'
  | 'marketing'
  | 'design'
  | 'sales'
  | 'data'
  | 'product'
  | 'general';

const VERTICAL_KEYWORDS: Record<VerticalBucket, string[]> = {
  electronics: [
    'electronics', 'ece', 'circuit', 'hardware', 'embedded', 'vlsi', 'fpga', 'pcb',
    'signal', 'analog', 'digital', 'microcontroller', 'iot', 'verilog', 'vhdl', 'matlab',
    'core electronics', 'communication',
  ],
  software: [
    'software', 'it', 'programming', 'coding', 'developer', 'engineer', 'react', 'node',
    'python', 'java', 'typescript', 'backend', 'frontend', 'fullstack', 'devops', 'api',
    'web', 'app', 'git', 'cloud', 'aws',
  ],
  marketing: [
    'marketing', 'campaign', 'content', 'seo', 'brand', 'social', 'copy', 'growth',
    'analytics', 'email', 'communication', 'client', 'presentation',
  ],
  design: [
    'design', 'ui', 'ux', 'figma', 'prototype', 'wireframe', 'visual', 'photoshop', 'user',
  ],
  sales: [
    'sales', 'crm', 'lead', 'negotiation', 'client', 'account', 'revenue', 'pipeline',
  ],
  data: [
    'data', 'analyst', 'analytics', 'sql', 'statistics', 'machine learning', 'bi', 'excel',
  ],
  product: [
    'product', 'roadmap', 'stakeholder', 'agile', 'scrum', 'requirements', 'pm',
  ],
  general: ['communication', 'leadership', 'teamwork', 'project', 'problem'],
};

function classifyVertical(vertical: string): VerticalBucket {
  const v = vertical.toLowerCase();
  if (/electron|ece|hardware|embedded|circuit|vlsi|fpga/.test(v)) return 'electronics';
  if (/market|content|seo|brand|growth/.test(v)) return 'marketing';
  if (/design|ui|ux|figma/.test(v)) return 'design';
  if (/sales|account exec|business develop/.test(v)) return 'sales';
  if (/data|analyst|ml|ai scientist/.test(v)) return 'data';
  if (/product/.test(v)) return 'product';
  if (/software|it\/|developer|engineer|frontend|backend|devops|fullstack/.test(v)) return 'software';
  return 'general';
}

function textBlob(profile: CandidateProfile): string {
  const parts: string[] = [
    ...(profile.skills || []),
    ...(profile.education || []).flatMap((e) => [e.degree, e.field, e.school, ...(e.highlights || [])]),
    ...(profile.experience || []).flatMap((e) => [e.title, e.company, e.description, ...(e.skills || [])]),
    ...(profile.projects || []).flatMap((p) => [p.name, p.description, ...(p.tags || [])]),
    ...(profile.certifications || []).map((c) => c.name),
  ].filter(Boolean) as string[];
  return parts.join(' ').toLowerCase();
}

function scoreRelevance(text: string, bucket: VerticalBucket): number {
  const keys = VERTICAL_KEYWORDS[bucket];
  let hits = 0;
  for (const k of keys) {
    if (text.includes(k)) hits += 1;
  }
  return hits;
}

function pickSkills(skills: string[], bucket: VerticalBucket, limit = 8): { keep: string[]; drop: string[] } {
  const keys = VERTICAL_KEYWORDS[bucket];
  const scored = skills.map((s) => {
    const lower = s.toLowerCase();
    const score = keys.some((k) => lower.includes(k) || k.includes(lower)) ? 2 : 0;
    // Transferable soft skills always partially relevant for marketing/sales
    const soft =
      (bucket === 'marketing' || bucket === 'sales') &&
      /communicat|present|client|analytics|content|leadership/.test(lower)
        ? 1.5
        : 0;
    // Coding skills for software; de-emphasize for marketing
    const tech =
      bucket === 'software' && /python|java|react|node|sql|git|aws/.test(lower)
        ? 2
        : bucket === 'marketing' && /python|java|c\+\+|embedded|circuit/.test(lower)
          ? -1
          : 0;
    return { s, score: score + soft + tech };
  });
  scored.sort((a, b) => b.score - a.score);
  const keep = scored.filter((x) => x.score > 0).slice(0, limit).map((x) => x.s);
  const drop = scored.filter((x) => x.score <= 0).map((x) => x.s);
  if (keep.length < 3) {
    return { keep: skills.slice(0, limit), drop: skills.slice(limit) };
  }
  return { keep, drop };
}

/**
 * Mapping step: identify which parts of the profile are relevant to the target vertical,
 * including transferable experience outside the candidate's "main" field.
 */
export function mapProfileToVertical(
  profile: CandidateProfile,
  vertical: string
): {
  bucket: VerticalBucket;
  relevantSkills: string[];
  deEmphasizedSkills: string[];
  relevantExperience: string[];
  relevantEducation: string[];
  transferableNotes: string[];
} {
  const bucket = classifyVertical(vertical);
  const blob = textBlob(profile);
  const skills = profile.skills?.length
    ? profile.skills
    : ['Python', 'C', 'Communication', 'MATLAB', 'Teamwork', 'Git', 'Presentation'];

  const { keep, drop } = pickSkills(skills, bucket);

  const relevantExperience = (profile.experience || [])
    .map((e) => {
      const t = `${e.title} ${e.description} ${(e.skills || []).join(' ')}`.toLowerCase();
      const score = scoreRelevance(t, bucket);
      // Transferable: client-facing / communication work counts for marketing
      const transfer =
        bucket === 'marketing' && /client|communicat|present|content|campaign|user/.test(t)
          ? 2
          : bucket === 'software' && /code|software|app|web|script|automat/.test(t)
            ? 2
            : 0;
      return { label: `${e.title || 'Role'}${e.company ? ` @ ${e.company}` : ''}`, score: score + transfer };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((x) => x.label);

  // Synthesize experience hints from blob when profile is sparse
  const syntheticExp: string[] = [];
  if (relevantExperience.length === 0) {
    if (bucket === 'electronics' && /circuit|embedded|ece|electronics|lab/.test(blob)) {
      syntheticExp.push('Core coursework & lab work in circuits / electronics');
    }
    if (bucket === 'software' && /python|java|project|coding|git/.test(blob)) {
      syntheticExp.push('Programming projects and software-adjacent coursework');
    }
    if (bucket === 'marketing' && /communicat|present|content|client|analytics/.test(blob)) {
      syntheticExp.push('Communication, content, or client-facing experience reframed for marketing');
    }
  }

  const relevantEducation = (profile.education || [])
    .map((e) => {
      const t = `${e.degree} ${e.field} ${(e.highlights || []).join(' ')}`.toLowerCase();
      const score = scoreRelevance(t, bucket);
      return {
        label: [e.degree, e.field].filter(Boolean).join(' — ') || e.school || 'Education',
        score,
      };
    })
    .filter((x) => x.score > 0 || bucket === 'general')
    .map((x) => x.label);

  const transferableNotes: string[] = [];
  if (bucket === 'software' && /electron|ece|hardware/.test(blob)) {
    transferableNotes.push(
      'Surfaced programming projects and coding-adjacent coursework from an electronics-leaning background'
    );
  }
  if (bucket === 'electronics' && /software|it/.test(blob)) {
    transferableNotes.push('Emphasized circuit/hardware labs and core ECE coursework over software detail');
  }
  if (bucket === 'marketing' && /software|engineer|developer|it/.test(blob)) {
    transferableNotes.push(
      'Foregrounded communication, campaigns, analytics, and client-facing work; de-emphasized deep programming detail'
    );
  }

  return {
    bucket,
    relevantSkills: keep,
    deEmphasizedSkills: drop.slice(0, 6),
    relevantExperience: relevantExperience.length ? relevantExperience : syntheticExp,
    relevantEducation:
      relevantEducation.length > 0
        ? relevantEducation
        : bucket === 'electronics'
          ? ['Electronics & Communication coursework']
          : [],
    transferableNotes,
  };
}

export function tailorResumeForVertical(
  profile: CandidateProfile,
  vertical: string
): TailoredResume {
  const mapped = mapProfileToVertical(profile, vertical);
  const baseScore = 78 + Math.min(18, mapped.relevantSkills.length * 2 + mapped.relevantExperience.length * 3);
  const score = Math.min(98, baseScore + (mapped.transferableNotes.length ? 2 : 0));

  const summaryByBucket: Record<VerticalBucket, string> = {
    electronics: `Electronics-focused professional with hands-on lab and hardware experience, tailored for ${vertical} roles.`,
    software: `Technically versatile candidate repositioned for ${vertical}, highlighting programming projects and software skills.`,
    marketing: `Profile reframed for ${vertical}, elevating communication, campaign, and analytics-adjacent experience.`,
    design: `Design-oriented narrative for ${vertical}, emphasizing UX/UI craft and product sense.`,
    sales: `Client-facing strengths highlighted for ${vertical}, with measurable relationship and pipeline focus.`,
    data: `Analytical profile for ${vertical}, centering data tools, insight generation, and quantitative coursework.`,
    product: `Cross-functional profile for ${vertical}, balancing technical literacy with stakeholder communication.`,
    general: `Tailored resume for ${vertical} based on the strongest transferable signals in your profile.`,
  };

  return {
    vertical,
    score,
    date: new Date().toISOString().split('T')[0],
    emphasis: [
      ...mapped.relevantSkills.slice(0, 4),
      ...mapped.relevantExperience.slice(0, 2),
    ],
    deEmphasized: mapped.deEmphasizedSkills,
    summary: summaryByBucket[mapped.bucket],
    highlightedSkills: mapped.relevantSkills,
    highlightedExperience: mapped.relevantExperience,
    highlightedEducation: mapped.relevantEducation,
    mappingNotes: mapped.transferableNotes.join(' ') || `Mapped profile signals to ${vertical} priorities.`,
  };
}

export function tailorResumesForVerticals(
  profile: CandidateProfile,
  verticals: string[]
): TailoredResume[] {
  return verticals.map((v) => tailorResumeForVertical(profile, v));
}
