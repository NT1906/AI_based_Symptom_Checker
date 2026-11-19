
/**
 * @file Symptom checker application shell.
 * Owner: Rutva · Task: S0-RUT-1, S2-RUT-3 · Requirements: NFR-05, NFR-09
 */
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { ChatAssessmentPage } from "./pages/ChatAssessmentPage";
import { restoreUnfinishedAssessment } from "./services/assessmentRecovery";
import { getCurrentPolicyVersion } from "./services/consentApi";
import { useConsentStore } from "./stores/consentStore";

/**
 * Checks the user's consent against the current policy and restores
 * an unfinished assessment before rendering the chat assessment page.
 *
 * @returns The consent check or the assessment page.
 */
function App() {
  const consentId = useConsentStore((state) => state.consentId);
  const policyVersion = useConsentStore((state) => state.policyVersion);

  const [isRestoring, setIsRestoring] = useState(true);
  const restoreStarted = useRef(false);

  const activePolicy = useQuery({
    queryKey: ["current-consent-policy"],
    queryFn: getCurrentPolicyVersion,
    enabled: Boolean(consentId),
  });

  const canRestore =
    Boolean(consentId) &&
    !activePolicy.isPending &&
    !activePolicy.isFetching &&
    !activePolicy.isError &&
    policyVersion === activePolicy.data;

  useEffect(() => {
    if (!canRestore || restoreStarted.current) return;

    restoreStarted.current = true;
    let mounted = true;

    restoreUnfinishedAssessment().finally(() => {
      if (mounted) {
        setIsRestoring(false);
      }
    });

    return () => {
      mounted = false;
    };
  }, [canRestore]);

  if (!consentId || activePolicy.isError) {
    return <Navigate to="/" replace />;
  }

  if (activePolicy.isPending || activePolicy.isFetching) {
    return <p role="status">Checking the privacy notice...</p>;
  }

  if (policyVersion !== activePolicy.data) {
    return <Navigate to="/" replace />;
  }

  if (isRestoring) {
    return <p role="status">Restoring your assessment...</p>;
  }

  return <ChatAssessmentPage consentId={consentId} />;
}

export default App;
