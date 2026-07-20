import PersonalDetailsForm from '@/components/candidate/PersonalDetailsForm';

export default function PersonalDetailsPage() {
  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-4xl mx-auto mb-8 text-center">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Personal Details</h1>
        <p className="text-slate-500">Provide some more context about yourself and your background.</p>
      </div>
      <PersonalDetailsForm />
    </div>
  );
}
