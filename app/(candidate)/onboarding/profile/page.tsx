import OnboardingForm from '@/components/candidate/OnboardingForm';

export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-4xl mx-auto mb-8 text-center">
        <h1 className="text-3xl font-bold text-ink mb-2">Complete your profile</h1>
        <p className="text-ink-muted">Let companies know more about you to find the best fit.</p>
      </div>
      <OnboardingForm />
    </div>
  );
}
