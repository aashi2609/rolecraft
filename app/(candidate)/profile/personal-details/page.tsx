import PersonalDetailsForm from '@/components/candidate/PersonalDetailsForm';

export default function PersonalDetailsPage() {
  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-4xl mx-auto mb-8 text-center">
        <h1 className="text-3xl font-bold text-ink mb-2">Personal Details</h1>
        <p className="text-ink-muted">Provide some more context about yourself and your background.</p>
      </div>
      <PersonalDetailsForm />
    </div>
  );
}
