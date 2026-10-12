import { useAssessmentStore } from "./stores/assessmentStore";

function App() {
  const messages = useAssessmentStore((state) => state.messages);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col px-6 py-12">
      <header className="mb-10">
        <p className="text-sm font-semibold uppercase tracking-widest text-teal-700">
          AI-Based Symptom Checker
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
          Symptom assessment
        </h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          Describe your symptoms to begin an informational assessment. This
          application does not provide a medical diagnosis or replace
          professional medical advice.
        </p>
      </header>

      <section
        aria-label="Assessment conversation"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        {messages.length === 0 ? (
          <p className="text-slate-500">
            Your conversation will appear here when the assessment flow is
            implemented.
          </p>
        ) : (
          <ul className="space-y-4">
            {messages.map((message) => (
              <li key={message.id} className="rounded-lg bg-slate-50 p-4">
                <p className="mb-1 text-xs font-semibold uppercase text-slate-500">
                  {message.role}
                </p>
                <p className="whitespace-pre-wrap text-slate-800">
                  {message.content}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="mt-6 text-sm text-slate-500">
        If you think you may be experiencing a medical emergency, contact local
        emergency services.
      </p>
    </main>
  );
}

export default App;
