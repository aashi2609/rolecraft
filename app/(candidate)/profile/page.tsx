import ProfileForm from '@/components/candidate/ProfileForm';

export default function ProfilePage() {
  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-4xl mx-auto mb-8 text-center">
        <h1 className="text-3xl font-bold text-ink mb-2">My Profile</h1>
        <p className="text-ink-muted">View and edit your complete candidate profile.</p>
      </div>
      <ProfileForm />
    </div>
  );
}
