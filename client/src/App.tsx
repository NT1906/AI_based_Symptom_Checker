/**
 * @file Symptom checker application shell.
 * Owner: Rutva · Task: S0-RUT-1, S2-NIS-13 · Requirements: NFR-08, NFR-09
 */
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { getCurrentPolicyVersion } from "./services/consentApi";
import { useConsentStore } from "./stores/consentStore";
import { ChatAssessmentPage } from "./pages/ChatAssessmentPage";

/**
 * Checks the user's consent against the current policy, then runs the
 * assessment flow (S2-NIS-13).
 *
 * @returns The consent check or the assessment page.
 */
function App() {
  const consentId = useConsentStore((state) => state.consentId);
  const policyVersion = useConsentStore((state) => state.policyVersion);
  const activePolicy = useQuery({
    queryKey: ["current-consent-policy"],
    queryFn: getCurrentPolicyVersion,
    enabled: Boolean(consentId),
  });
  if (!consentId || activePolicy.isError) {
    return <Navigate to="/" replace />;
  }
  if (activePolicy.isPending || activePolicy.isFetching) {
    return <p role="status">Checking the privacy notice…</p>;
  }
  if (policyVersion !== activePolicy.data) {
    return <Navigate to="/" replace />;
  }

  return <ChatAssessmentPage consentId={consentId} />;
}

export default App;
