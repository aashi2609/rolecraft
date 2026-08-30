/** Profile completeness and display helpers for candidate UI. */

export function getDisplayName(profile: Record<string, unknown> | null | undefined): string {
  if (!profile) return '';
  const fullName = profile.full_name || (profile.weblinks as any)?.display_name;
  if (typeof fullName === 'string' && fullName.trim()) return fullName.trim();
  const email = profile.email;
  if (typeof email === 'string' && email.includes('@')) return email.split('@')[0];
  return '';
}

export function getProfileLocation(profile: Record<string, unknown> | null | undefined): string {
  if (!profile) return '';
  const locs = profile.preferred_locations as string[] | undefined;
  if (locs?.length) return locs[0];
  const addr = profile.present_address;
  if (typeof addr === 'string' && addr.trim()) return addr.split(',')[0].trim();
  return '';
}

export function computeProfileCompleteness(profile: Record<string, unknown> | null | undefined): number {
  if (!profile) return 0;
  const checks = [
    Boolean(getDisplayName(profile)),
    Boolean(profile.career_level),
    Array.isArray(profile.skills) && profile.skills.length > 0,
    Array.isArray(profile.education) && profile.education.length > 0,
    Array.isArray(profile.experience) && profile.experience.length > 0,
    Boolean(profile.email),
  ];
  const done = checks.filter(Boolean).length;
  return Math.round((done / checks.length) * 100);
}
