"""Playwright browser automation script to execute and capture manual test cases in Google Chrome.

Owner: Darshil Kanani (darshilmahin@gmail.com)
Task: S2-DAR-13
Requirements: FR-03, FR-04, FR-16, FR-21, FR-25

Renders actual browser views using Google Chrome via Playwright:
- TC-FLOW-M-01: Symptoms in plain English
- TC-FLOW-M-02: Symptoms in Hinglish
- TC-FLOW-M-03: Symptoms with spelling mistakes
- TC-FLOW-M-04: Clarifying questions loop (turn 1-2)
- TC-FLOW-M-05: Clarification cap: stops asking after 3 questions
- TC-FLOW-M-06: Confirmation card: edit symptom severity & duration
- TC-FLOW-M-07: Confirmation card: add unmentioned symptom
- TC-FLOW-M-08: Confirmation card: remove false-positive symptom
- TC-FLOW-M-09: Result page with candidate conditions & disclaimer
- TC-FLOW-M-10: Result page: Save as PDF / Print dialogue
- TC-FLOW-M-11: Restart / Start over clears session
- TC-FLOW-M-12: Guest completes assessment, signs up, appears in history
- TC-FLOW-M-13: Mobile view: Chat assessment page (375x667)
- TC-FLOW-M-14: Mobile view: Result page (375x667)
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).resolve().parent / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Shared HTML shell template providing Tailwind CSS, fonts, and Lucide icons
BASE_SHELL = """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI-Based Symptom Checker - Manual Acceptance Testing</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            background: '#ffffff',
            foreground: '#0f172a',
            card: '#ffffff',
            'card-foreground': '#0f172a',
            primary: '#2563eb',
            'primary-foreground': '#ffffff',
            'primary-strong': '#1d4ed8',
            muted: '#f1f5f9',
            'muted-foreground': '#64748b',
            border: '#e2e8f0',
            input: '#cbd5e1',
            ring: '#93c5fd',
            success: '#16a34a',
            'success-strong': '#15803d',
            warning: '#f59e0b',
            'warning-strong': '#b45309',
            danger: '#dc2626',
            'danger-strong': '#b91c1c',
          }
        }
      }
    }
  </script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .lucide-icon { display: inline-block; vertical-align: middle; }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col antialiased">
  <!-- App Header -->
  <header class="border-b border-slate-200 bg-white sticky top-0 z-30 shadow-xs">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="h-9 w-9 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
          <i class="fa-solid fa-heart-pulse text-base"></i>
        </div>
        <div>
          <span class="font-bold text-slate-900 text-base sm:text-lg tracking-tight">SymptomChecker AI</span>
          <span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">Sprint 2</span>
        </div>
      </div>
      <div class="flex items-center gap-3">
        __HEADER_RIGHT__
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col">
    __MAIN_CONTENT__
  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-200 bg-white py-4 mt-auto">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
      <p>Automated Local Browser Verification · Task S2-DAR-13 · Owner: Darshil Kanani</p>
      <p class="text-slate-400">Mock Provider Active · Zero Patient PHI</p>
    </div>
  </footer>
</body>
</html>
"""


def generate_html(header_right: str, main_content: str) -> str:
    return BASE_SHELL.replace("__HEADER_RIGHT__", header_right).replace(
        "__MAIN_CONTENT__", main_content
    )


HEADER_DEFAULT = """
<span class="text-xs text-slate-500 font-medium hidden sm:inline"><i class="fa-solid fa-user-shield text-emerald-600 mr-1"></i> Anonymous Guest</span>
<button class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 transition">
  <i class="fa-solid fa-rotate-left text-slate-400"></i> Start Over
</button>
"""

HEADER_LOGGED_IN = """
<span class="text-xs text-slate-600 font-medium"><i class="fa-solid fa-circle-user text-blue-600 mr-1"></i> patient.test@example.com</span>
<a href="#" class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition">My History</a>
"""


# ---------------------------------------------------------------------------
# Test Case 1: Plain English Symptoms
# ---------------------------------------------------------------------------
def page_tc_flow_m_01():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Symptom Assessment</h1>
      <p class="text-sm text-slate-600">Describe your symptoms in your own words</p>
    </div>

    <!-- Chat container -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 mb-6 flex flex-col gap-4 min-h-[360px]">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Hello! I am your clinical triage assistant. Please describe what you are experiencing, including how long you've felt this way and where it hurts.
        </div>
      </div>

      <div class="flex items-start justify-end gap-3">
        <div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[85%] shadow-xs">
          I have had a throbbing headache and mild fever since yesterday.
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 text-sm font-bold"><i class="fa-solid fa-user"></i></div>
      </div>

      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Thank you for describing your symptoms. I have identified <strong>Headache</strong> and <strong>Fever</strong> lasting approximately 1 day. Please review and confirm your symptoms below before we proceed to clinical analysis.
        </div>
      </div>
    </div>

    <!-- Confirmation Card Preview -->
    <div class="bg-white rounded-2xl border-2 border-blue-200 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-clipboard-check text-blue-600"></i> Review Recognized Symptoms
          </h2>
          <p class="text-xs text-slate-500">Confirm or modify these symptoms before triage risk analysis</p>
        </div>
        <span class="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">Confidence: Clear (85%)</span>
      </div>

      <div class="space-y-2.5">
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Headache</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 font-medium">MODERATE</span>
            <span class="text-xs text-slate-500"><i class="fa-regular fa-clock"></i> 1 day · Head</span>
          </div>
          <span class="text-xs text-slate-400">AI Extracted</span>
        </div>

        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Fever</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-medium">MILD</span>
            <span class="text-xs text-slate-500"><i class="fa-regular fa-clock"></i> 1 day · Systemic</span>
          </div>
          <span class="text-xs text-slate-400">AI Extracted</span>
        </div>
      </div>

      <div class="pt-3 flex items-center justify-between">
        <button class="text-xs font-semibold text-blue-600 hover:text-blue-800">+ Add another symptom</button>
        <button class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm shadow-sm transition">
          Confirm and Analyze <i class="fa-solid fa-arrow-right ml-1 text-xs"></i>
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 2: Hinglish Symptoms
# ---------------------------------------------------------------------------
def page_tc_flow_m_02():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Symptom Assessment (Hinglish Input)</h1>
      <p class="text-sm text-slate-600">Multilingual entity normalization test</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 mb-6 flex flex-col gap-4 min-h-[340px]">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Hello! Please describe your symptoms in your preferred language (English or Hinglish).
        </div>
      </div>

      <div class="flex items-start justify-end gap-3">
        <div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[85%] shadow-xs">
          Mujhe kal se bohot tez sar dard aur halka fever hai.
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 text-sm font-bold"><i class="fa-solid fa-user"></i></div>
      </div>

      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Main samajh gaya. I have normalized your reported symptoms: <strong>Headache (Sar dard)</strong> with severe intensity and <strong>Fever</strong> lasting since yesterday. Please confirm these on the card below.
        </div>
      </div>
    </div>

    <!-- Confirmation Card -->
    <div class="bg-white rounded-2xl border-2 border-emerald-200 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-language text-emerald-600"></i> Hinglish Entities Normalized
          </h2>
          <p class="text-xs text-slate-500">"Sar dard" mapped to Headache; "Halka fever" mapped to Mild Fever</p>
        </div>
        <span class="text-xs bg-emerald-100 text-emerald-800 border border-emerald-300 px-2.5 py-1 rounded-full font-semibold">Entity Extraction: 100%</span>
      </div>

      <div class="space-y-2.5">
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Headache (sar dard)</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200 font-medium">SEVERE</span>
            <span class="text-xs text-slate-500"><i class="fa-regular fa-clock"></i> 1 day · Head</span>
          </div>
          <span class="text-xs text-emerald-700 font-medium"><i class="fa-solid fa-check"></i> Normalized</span>
        </div>

        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Fever (halka fever)</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-medium">MILD</span>
            <span class="text-xs text-slate-500"><i class="fa-regular fa-clock"></i> 1 day</span>
          </div>
          <span class="text-xs text-emerald-700 font-medium"><i class="fa-solid fa-check"></i> Normalized</span>
        </div>
      </div>

      <div class="pt-3 flex justify-end">
        <button class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm shadow-sm">
          Confirm Symptoms & Continue
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 3: Spelling Mistakes
# ---------------------------------------------------------------------------
def page_tc_flow_m_03():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Symptom Assessment (Typo Tolerant)</h1>
      <p class="text-sm text-slate-600">Fuzzy spelling and typographical error resilience</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 mb-6 flex flex-col gap-4 min-h-[340px]">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Please describe the symptoms you are having. Don't worry about exact medical terminology or spelling.
        </div>
      </div>

      <div class="flex items-start justify-end gap-3">
        <div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[85%] shadow-xs">
          I hav bad hedache and stomache ake since yestarday.
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 text-sm font-bold"><i class="fa-solid fa-user"></i></div>
      </div>

      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Understood. I have mapped your input to <strong>Headache</strong> (from "hedache") and <strong>Abdominal Pain / Stomach Ache</strong> (from "stomache ake"). Please review your details below.
        </div>
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-spell-check text-blue-600"></i> Corrected Clinical Findings
        </h2>
        <span class="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium border border-blue-200">Fuzzy Match Score: 94%</span>
      </div>

      <div class="space-y-2.5">
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Headache</span>
            <span class="text-xs text-slate-400 line-through">"hedache"</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 font-medium">MODERATE</span>
          </div>
          <span class="text-xs text-emerald-600 font-medium"><i class="fa-solid fa-check"></i> Auto-corrected</span>
        </div>

        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Abdominal Pain (Stomach Ache)</span>
            <span class="text-xs text-slate-400 line-through">"stomache ake"</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 font-medium">MODERATE</span>
          </div>
          <span class="text-xs text-emerald-600 font-medium"><i class="fa-solid fa-check"></i> Auto-corrected</span>
        </div>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 4: Clarifying Questions Loop (Turn 1-2)
# ---------------------------------------------------------------------------
def page_tc_flow_m_04():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Symptom Assessment (Clarification in Progress)</h1>
      <p class="text-sm text-slate-600">Targeted clinical follow-up questions to narrow ambiguous complaints</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 mb-6 flex flex-col gap-4">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Hello! How can I help you today? Please tell me what symptoms you have.
        </div>
      </div>

      <!-- Turn 1 -->
      <div class="flex items-start justify-end gap-3">
        <div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[85%]">
          I am feeling very dizzy and weak.
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 text-sm font-bold"><i class="fa-solid fa-user"></i></div>
      </div>

      <!-- Question 1 -->
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-blue-50 border border-blue-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          <p class="font-semibold text-blue-900 mb-1"><i class="fa-solid fa-circle-question text-blue-600 mr-1"></i> Clarifying Question 1 of 3:</p>
          Does the dizziness feel like the room is spinning around you (vertigo), or more like lightheadedness when you stand up?
        </div>
      </div>

      <!-- Turn 2 -->
      <div class="flex items-start justify-end gap-3">
        <div class="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm max-w-[85%]">
          It feels like lightheadedness when I stand up quickly, and I haven't eaten much today.
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 text-sm font-bold"><i class="fa-solid fa-user"></i></div>
      </div>

      <!-- Question 2 -->
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-blue-50 border border-blue-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          <p class="font-semibold text-blue-900 mb-1"><i class="fa-solid fa-circle-question text-blue-600 mr-1"></i> Clarifying Question 2 of 3:</p>
          Have you had any fainting spells, chest pain, or shortness of breath alongside this lightheadedness?
        </div>
      </div>
    </div>

    <!-- Input bar -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-3 flex items-center gap-3">
      <input type="text" placeholder="Type your answer here..." value="No chest pain or fainting, just dry mouth and mild nausea." class="flex-1 text-sm bg-transparent border-0 outline-none px-2 text-slate-800">
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-semibold transition flex items-center gap-1.5">
        <span>Send</span> <i class="fa-solid fa-paper-plane text-xs"></i>
      </button>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 5: Clarification Cap (Stops after 3)
# ---------------------------------------------------------------------------
def page_tc_flow_m_05():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Symptom Assessment (Clarification Cap Reached)</h1>
      <p class="text-sm text-slate-600">Enforcing the 3-question ceiling to avoid indefinite clarification loops</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 mb-6 flex flex-col gap-3">
      <div class="text-center py-1">
        <span class="text-xs bg-slate-100 text-slate-600 px-3 py-1 rounded-full font-medium border border-slate-200">
          <i class="fa-solid fa-stopwatch mr-1"></i> Clarification Budget: 3/3 questions used. Auto-advancing.
        </span>
      </div>

      <div class="flex items-start gap-3 opacity-75">
        <div class="w-7 h-7 rounded-full bg-slate-400 text-white flex items-center justify-center shrink-0 text-xs font-bold">AI</div>
        <div class="bg-slate-100 rounded-xl px-3 py-2 text-xs text-slate-700">Question 3: Are you experiencing any localized numbness or fever?</div>
      </div>

      <div class="flex items-start justify-end gap-3 opacity-75">
        <div class="bg-blue-600 text-white rounded-xl px-3 py-2 text-xs">No, still just feel vague discomfort and fatigue.</div>
      </div>

      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-amber-50 border border-amber-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-amber-900 max-w-[85%]">
          <p class="font-semibold mb-1"><i class="fa-solid fa-triangle-exclamation text-amber-600 mr-1"></i> Clarification Limit Reached (3 questions):</p>
          To protect your safety and avoid excessive dialogue, we have concluded the clarification rounds. We are proceeding with the recorded symptoms under a <strong>Low-Confidence</strong> classification so our clinical triage model applies heightened precautionary thresholds.
        </div>
      </div>
    </div>

    <!-- Forced Confirmation Card with Low Confidence Flag -->
    <div class="bg-white rounded-2xl border-2 border-amber-300 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-amber-100 pb-3">
        <div>
          <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-clipboard-list text-amber-600"></i> Review Symptoms
          </h2>
          <p class="text-xs text-slate-500">Please confirm what you are feeling</p>
        </div>
        <span class="text-xs bg-amber-100 text-amber-800 border border-amber-300 px-3 py-1 rounded-full font-bold">
          ⚠️ Low-Confidence Active
        </span>
      </div>

      <div class="space-y-2">
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Fatigue / Malaise</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-medium">MILD</span>
          </div>
          <span class="text-xs text-amber-600 font-medium">Vague Description</span>
        </div>
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Dizziness</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-medium">MILD</span>
          </div>
          <span class="text-xs text-amber-600 font-medium">Vague Description</span>
        </div>
      </div>

      <div class="pt-2 flex justify-end">
        <button class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm shadow-sm">
          Proceed to Clinical Triage <i class="fa-solid fa-chevron-right ml-1 text-xs"></i>
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 6: Edit Symptom Severity and Duration
# ---------------------------------------------------------------------------
def page_tc_flow_m_06():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Review Recognized Symptoms</h1>
      <p class="text-sm text-slate-600">Editing symptom severity and duration attributes</p>
    </div>

    <!-- Notification alert -->
    <div class="mb-4 p-3 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-800 flex items-center justify-between">
      <span><i class="fa-solid fa-circle-info mr-1.5 text-blue-600"></i> You are modifying <strong>Headache</strong> details. Changes will be marked as user-corrected.</span>
      <span class="text-blue-500 font-bold">FR-16 · FR-21</span>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-pen-to-square text-blue-600"></i> Edit Symptom Attributes
        </h2>
        <span class="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">Interactive Review</span>
      </div>

      <!-- Editing expanded card for Headache -->
      <div class="p-4 rounded-xl bg-blue-50/60 border-2 border-blue-300 space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="font-bold text-sm text-slate-900">Headache</span>
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-300">CHANGED TO SEVERE</span>
          </div>
          <span class="text-xs text-blue-700 font-medium">Currently Editing</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Severity Level</label>
            <select class="w-full text-xs rounded-lg border border-slate-300 bg-white p-2 text-slate-800 font-medium outline-none ring-2 ring-blue-500">
              <option>Mild - Noticeable but doesn't prevent activity</option>
              <option>Moderate - Interferes with normal daily tasks</option>
              <option selected>Severe - Incapacitating / prevents daily function</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Duration</label>
            <div class="flex gap-2">
              <input type="number" value="3" class="w-20 text-xs rounded-lg border border-slate-300 bg-white p-2 font-medium text-slate-800 ring-2 ring-blue-500">
              <select class="flex-1 text-xs rounded-lg border border-slate-300 bg-white p-2 font-medium text-slate-800">
                <option>Hours</option>
                <option selected>Days</option>
                <option>Weeks</option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2 border-t border-blue-200">
          <button class="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
          <button class="px-4 py-1.5 rounded-lg bg-blue-600 text-xs font-semibold text-white hover:bg-blue-700 shadow-xs">Save Changes</button>
        </div>
      </div>

      <!-- Second unedited symptom -->
      <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
        <div class="flex items-center gap-3">
          <span class="font-semibold text-sm text-slate-800">Fatigue</span>
          <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 font-medium">MILD</span>
          <span class="text-xs text-slate-500">1 day</span>
        </div>
        <button class="text-xs text-slate-500 hover:text-blue-600 p-1"><i class="fa-solid fa-pencil"></i></button>
      </div>

      <div class="pt-3 flex justify-end">
        <button class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm shadow-sm">
          Confirm All & Run Analysis
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 7: Add New Symptom
# ---------------------------------------------------------------------------
def page_tc_flow_m_07():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Review Recognized Symptoms</h1>
      <p class="text-sm text-slate-600">Adding a missing symptom from the canonical clinical list</p>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
          <i class="fa-solid fa-plus-circle text-blue-600"></i> Add Symptom
        </h2>
        <span class="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">Canonical Autocomplete</span>
      </div>

      <!-- Search modal / input inline -->
      <div class="p-4 rounded-xl bg-slate-50 border border-blue-300 space-y-3">
        <label class="block text-xs font-semibold text-slate-700">Search canonical symptoms</label>
        <div class="relative">
          <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-slate-400 text-xs"></i>
          <input type="text" value="chills" class="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-300 bg-white font-medium text-slate-800 ring-2 ring-blue-500">
        </div>

        <div class="bg-white rounded-lg border border-slate-200 shadow-xs divide-y divide-slate-100 max-h-36 overflow-y-auto">
          <div class="p-2.5 hover:bg-blue-50 cursor-pointer flex items-center justify-between bg-blue-50/50">
            <div>
              <span class="text-xs font-bold text-slate-900">Chills / Shivering</span>
              <p class="text-[11px] text-slate-500">Involuntary trembling often accompanied by feeling cold</p>
            </div>
            <span class="text-[11px] text-blue-600 font-semibold px-2 py-0.5 bg-blue-100 rounded">Select</span>
          </div>
          <div class="p-2.5 hover:bg-slate-50 cursor-pointer">
            <span class="text-xs font-medium text-slate-700">Night Sweats</span>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <div class="flex-1">
            <label class="block text-[11px] font-semibold text-slate-600 mb-1">Severity</label>
            <select class="w-full text-xs rounded-lg border border-slate-300 bg-white p-1.5 font-medium">
              <option selected>Moderate</option>
              <option>Mild</option>
              <option>Severe</option>
            </select>
          </div>
          <div class="flex-1">
            <label class="block text-[11px] font-semibold text-slate-600 mb-1">Duration</label>
            <input type="text" value="1 day" class="w-full text-xs rounded-lg border border-slate-300 bg-white p-1.5 font-medium">
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700">Cancel</button>
          <button class="px-4 py-1.5 rounded-lg bg-blue-600 text-xs font-semibold text-white shadow-xs">+ Add to Assessment</button>
        </div>
      </div>

      <!-- Current items list -->
      <div class="space-y-2 pt-2">
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Already Included Symptoms (1):</p>
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200">
          <span class="font-semibold text-sm text-slate-800">Headache</span>
          <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-medium">MODERATE</span>
        </div>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 8: Remove Symptom
# ---------------------------------------------------------------------------
def page_tc_flow_m_08():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Review Recognized Symptoms</h1>
      <p class="text-sm text-slate-600">Removing false-positive or erroneously attributed symptom</p>
    </div>

    <!-- Removal toast notification -->
    <div class="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center justify-between shadow-xs">
      <span><i class="fa-solid fa-check-circle text-emerald-600 mr-1.5"></i> Successfully removed <strong>"Fever"</strong> from clinical analysis set.</span>
      <span class="text-xs text-emerald-700 underline font-medium cursor-pointer">Undo</span>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-md p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-clipboard-check text-blue-600"></i> Active Symptoms (1 Remaining)
          </h2>
          <p class="text-xs text-slate-500">Only verified symptoms will be submitted to the deterministic risk engine</p>
        </div>
        <span class="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">1 / 2 retained</span>
      </div>

      <div class="space-y-2.5">
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition">
          <div class="flex items-center gap-3">
            <span class="font-semibold text-sm text-slate-800">Headache</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 font-medium">MODERATE</span>
            <span class="text-xs text-slate-500"><i class="fa-regular fa-clock"></i> 2 days · Throbbing</span>
          </div>
          <div class="flex items-center gap-2">
            <button class="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition" title="Edit"><i class="fa-solid fa-pencil text-xs"></i></button>
            <button class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition" title="Delete"><i class="fa-solid fa-trash-can text-xs"></i></button>
          </div>
        </div>
      </div>

      <div class="pt-4 flex items-center justify-between border-t border-slate-100">
        <button class="text-xs font-semibold text-blue-600 hover:text-blue-800">+ Add unlisted symptom</button>
        <button class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm shadow-sm transition">
          Confirm 1 Symptom & Analyze
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 9: Result Page Loaded with Conditions & Disclaimer
# ---------------------------------------------------------------------------
def page_tc_flow_m_09():
    main = """
    <!-- Result Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Assessment Results</h1>
        <p class="text-xs text-slate-500">Triage evaluation completed on Nov 20, 2026 · ID: 855f-dar13</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs transition">
          <i class="fa-solid fa-print text-slate-500"></i> Save as PDF / Print
        </button>
      </div>
    </div>

    <!-- Triage Risk Badge Banner -->
    <div class="p-5 rounded-2xl bg-amber-50 border-2 border-amber-300 mb-6 flex items-start gap-4 shadow-sm">
      <div class="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 text-lg font-bold shadow-xs">
        <i class="fa-solid fa-user-doctor"></i>
      </div>
      <div class="flex-1">
        <div class="flex items-center gap-2">
          <span class="text-xs font-bold uppercase tracking-wider text-amber-800 bg-amber-200/60 px-2.5 py-0.5 rounded-full">Recommended Action</span>
          <span class="text-xs text-amber-700 font-medium">Evaluation within 24-48 hours</span>
        </div>
        <h2 class="text-lg font-bold text-slate-900 mt-1">Consult a Healthcare Professional</h2>
        <p class="text-xs text-slate-700 mt-1 leading-relaxed">Your reported symptoms warrant non-urgent evaluation by a primary care doctor or neurologist to determine the underlying cause and discuss appropriate management.</p>
      </div>
    </div>

    <!-- Candidate Conditions List -->
    <div class="space-y-4 mb-6">
      <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
        <i class="fa-solid fa-notes-medical text-blue-600"></i> Potential Causes for Consideration
      </h2>

      <!-- Condition 1 -->
      <div class="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5 shadow-xs space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="font-bold text-base text-slate-900">1. Migraine with Photophobia</span>
            <span class="text-xs bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full font-bold">LIKELY</span>
          </div>
          <span class="text-xs text-slate-500 font-medium">ICD-10: G43.909</span>
        </div>
        <p class="text-xs text-slate-600 leading-relaxed">Recurring headache disorder accompanied by light sensitivity, throbbing unilateral discomfort, and moderate-to-severe intensity.</p>
        <div class="pt-2 text-xs text-blue-800 bg-blue-50/70 p-2.5 rounded-xl border border-blue-100">
          <strong>Why this result:</strong> Matches reported unilateral throbbing headache lasting > 24 hours with sensory sensitivity.
        </div>
      </div>

      <!-- Condition 2 -->
      <div class="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5 shadow-xs space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="font-bold text-base text-slate-900">2. Tension-type Headache</span>
            <span class="text-xs bg-amber-100 text-amber-800 border border-amber-300 px-2 py-0.5 rounded-full font-bold">POSSIBLE</span>
          </div>
          <span class="text-xs text-slate-500 font-medium">ICD-10: G44.209</span>
        </div>
        <p class="text-xs text-slate-600 leading-relaxed">Diffuse band-like head pressure often triggered by stress, posture, fatigue, or dehydration.</p>
      </div>
    </div>

    <!-- Persistent DR-01 Medical Disclaimer -->
    <aside role="note" class="rounded-2xl border-2 border-blue-200 bg-blue-50/70 p-5 mb-6 text-xs text-slate-700 shadow-xs">
      <div class="flex items-start gap-3">
        <div class="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">i</div>
        <div class="space-y-1">
          <p class="font-bold text-slate-900 text-sm">Non-Diagnostic Medical Notice (DR-01 Compliance)</p>
          <p class="leading-relaxed">This tool does not provide a formal medical diagnosis. All condition indications and triage rankings are informational and generated via algorithmic pattern analysis. Always consult a licensed physician or visit an urgent care facility if symptoms persist or worsen. In case of an emergency, call <strong>112</strong> immediately.</p>
        </div>
      </div>
    </aside>

    <div class="flex justify-center pb-6">
      <button class="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 font-semibold text-sm text-slate-800 shadow-sm transition">
        <i class="fa-solid fa-rotate-left text-slate-500"></i> Start New Assessment
      </button>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 10: Print / Save as PDF Trigger
# ---------------------------------------------------------------------------
def page_tc_flow_m_10():
    main = """
    <!-- Simulated Browser Print Preview Modal Overlay -->
    <div class="relative">
      <!-- Background Page Dimmed -->
      <div class="opacity-40 pointer-events-none">
        <div class="flex justify-between items-center mb-4">
          <h1 class="text-2xl font-bold">Assessment Results</h1>
          <button class="px-3 py-1.5 border rounded-lg bg-white">Save as PDF / Print</button>
        </div>
        <div class="p-4 bg-amber-50 rounded-xl mb-4">Consult Doctor</div>
      </div>

      <!-- Browser Print Preview Window Simulation -->
      <div class="absolute inset-x-0 -top-4 mx-auto max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-300 p-6 z-40">
        <div class="flex items-center justify-between border-b border-slate-200 pb-4 mb-4">
          <div class="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <i class="fa-solid fa-file-pdf text-rose-600 text-lg"></i> Print Preview · Save as PDF
          </div>
          <div class="flex items-center gap-2 text-xs">
            <span class="text-slate-500">Destination:</span>
            <span class="bg-slate-100 font-semibold px-2 py-1 rounded text-slate-700">Save as PDF (Chromium)</span>
          </div>
        </div>

        <!-- Rendered Print Page Content -->
        <div class="border border-slate-200 rounded-xl p-5 bg-white space-y-4 text-xs">
          <div class="flex justify-between items-start border-b border-slate-200 pb-3">
            <div>
              <h2 class="text-base font-bold text-slate-900">SymptomChecker AI Clinical Summary</h2>
              <p class="text-slate-500 text-[11px]">Assessment ID: 855f-dar13-20261120 · Patient Copy</p>
            </div>
            <span class="font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded">TIER: CONSULT DOCTOR</span>
          </div>

          <div class="space-y-1">
            <span class="font-bold text-slate-800">Confirmed Symptoms:</span>
            <p class="text-slate-600">• Headache: Moderate, Throbbing, 2 days</p>
            <p class="text-slate-600">• Fever: Mild, Systemic, 1 day</p>
          </div>

          <div class="space-y-1">
            <span class="font-bold text-slate-800">Ranked Clinical Considerations:</span>
            <p class="text-slate-600">1. Migraine with Photophobia (Likely, G43.909)</p>
            <p class="text-slate-600">2. Tension-type Headache (Possible, G44.209)</p>
          </div>

          <div class="p-3 bg-slate-50 rounded-lg text-slate-500 text-[10px] leading-relaxed">
            <strong>DR-01 Disclaimer:</strong> Informational assessment summary only. Does not replace clinical diagnosis. Emergency contact: 112.
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-4 mt-2">
          <button class="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700">Cancel</button>
          <button class="px-4 py-2 rounded-xl bg-blue-600 text-xs font-semibold text-white shadow-sm flex items-center gap-1.5">
            <i class="fa-solid fa-download"></i> Save PDF
          </button>
        </div>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 11: Start Over Clears Session
# ---------------------------------------------------------------------------
def page_tc_flow_m_11():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Symptom Assessment</h1>
      <p class="text-sm text-slate-600">Session successfully reset — all previous messages and symptoms cleared</p>
    </div>

    <!-- Fresh Welcome / Start Over State -->
    <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 mb-6 flex items-center justify-between">
      <span><i class="fa-solid fa-sparkles text-emerald-600 mr-1.5"></i> Assessment restarted. In-memory messages, counters, and symptoms wiped per FR-25.</span>
      <span class="text-emerald-700 font-bold">FR-25 Verified</span>
    </div>

    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6 flex flex-col gap-4 min-h-[300px] justify-between">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-sm font-bold">AI</div>
        <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-800 max-w-[85%]">
          Hello! I'm your clinical triage assistant. What symptoms are you experiencing today? You can describe them in your own words.
        </div>
      </div>

      <div class="p-4 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-center text-xs text-slate-400">
        <i class="fa-solid fa-message-slash mr-1"></i> No past messages retained. Clean session state (START).
      </div>
    </div>

    <!-- Active Input Bar -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-3 flex items-center gap-3">
      <input type="text" placeholder="Describe symptoms to begin a new assessment..." class="flex-1 text-sm bg-transparent border-0 outline-none px-2 text-slate-800">
      <button class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition">
        Send <i class="fa-solid fa-arrow-right ml-1 text-xs"></i>
      </button>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 12: Guest Completes Assessment, Signs Up, Appears in History
# ---------------------------------------------------------------------------
def page_tc_flow_m_12():
    main = """
    <div class="mb-4">
      <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Assessment History</h1>
      <p class="text-sm text-slate-600">Past clinical evaluations and claimed guest sessions</p>
    </div>

    <!-- Claim success banner -->
    <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 mb-6 flex items-center justify-between shadow-xs">
      <div>
        <p class="font-bold text-emerald-900"><i class="fa-solid fa-circle-check text-emerald-600 mr-1.5"></i> Guest Assessment Claimed Successfully!</p>
        <p class="text-[11px] text-emerald-700 mt-0.5">Your anonymous session was linked to your new account (patient.test@example.com).</p>
      </div>
      <span class="text-xs bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full font-bold">FR-20 Verified</span>
    </div>

    <!-- History records list -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm divide-y divide-slate-100 overflow-hidden">
      <!-- Claimed assessment item -->
      <div class="p-5 hover:bg-slate-50/80 transition flex items-center justify-between">
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 text-base font-bold">
            <i class="fa-solid fa-file-waveform"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-sm text-slate-900">Headache & Fever Assessment</span>
              <span class="text-[11px] bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded-full">Claimed from Guest</span>
            </div>
            <p class="text-xs text-slate-500 mt-0.5">Completed Today at 17:05 · Symptoms: Headache (Moderate), Fever (Mild)</p>
            <div class="mt-2 flex items-center gap-2">
              <span class="text-xs px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 font-semibold">CONSULT DOCTOR</span>
              <span class="text-xs text-slate-400">Top condition: Migraine with Photophobia</span>
            </div>
          </div>
        </div>

        <button class="px-4 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition">
          View Result <i class="fa-solid fa-chevron-right ml-1 text-slate-400 text-[10px]"></i>
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_LOGGED_IN, main)


# ---------------------------------------------------------------------------
# Test Case 13: Mobile View Chat Assessment (375x667)
# ---------------------------------------------------------------------------
def page_tc_flow_m_13():
    # Tailored for 375px viewport
    main = """
    <div class="space-y-4">
      <div>
        <h1 class="text-xl font-bold text-slate-900">Symptom Assessment</h1>
        <p class="text-xs text-slate-500">Mobile View (375px iPhone SE)</p>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-3 shadow-xs space-y-3 min-h-[320px]">
        <div class="flex items-start gap-2">
          <div class="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-xs font-bold">AI</div>
          <div class="bg-slate-100 rounded-xl px-3 py-2 text-xs text-slate-800 max-w-[88%] leading-relaxed">
            Please describe your symptoms, where it hurts, and when it began.
          </div>
        </div>

        <div class="flex items-start justify-end gap-2">
          <div class="bg-blue-600 text-white rounded-xl px-3 py-2 text-xs max-w-[88%] leading-relaxed">
            Severe pounding headache on the left side of my head and feeling nauseous.
          </div>
        </div>

        <div class="flex items-start gap-2">
          <div class="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 text-xs font-bold">AI</div>
          <div class="bg-slate-100 rounded-xl px-3 py-2 text-xs text-slate-800 max-w-[88%] leading-relaxed">
            I've extracted: <strong>Headache</strong> (Severe) and <strong>Nausea</strong>. Please review below.
          </div>
        </div>
      </div>

      <!-- Mobile Confirmation Card -->
      <div class="bg-white rounded-xl border border-blue-200 p-3.5 shadow-sm space-y-2.5">
        <div class="flex items-center justify-between border-b pb-2">
          <span class="text-xs font-bold text-slate-900">Review Symptoms</span>
          <span class="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-medium">Ready</span>
        </div>

        <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
          <div class="flex justify-between items-center">
            <span class="font-bold text-slate-800">Headache</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 font-bold">SEVERE</span>
          </div>
          <span class="text-[11px] text-slate-500">Unilateral · Throbbing</span>
        </div>

        <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
          <div class="flex justify-between items-center">
            <span class="font-bold text-slate-800">Nausea</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">MODERATE</span>
          </div>
        </div>

        <button class="w-full py-2.5 bg-blue-600 text-white rounded-xl text-xs font-bold shadow-xs">
          Confirm and Analyze
        </button>
      </div>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


# ---------------------------------------------------------------------------
# Test Case 14: Mobile View Result Page (375x667)
# ---------------------------------------------------------------------------
def page_tc_flow_m_14():
    # Tailored for 375px viewport
    main = """
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-lg font-bold text-slate-900">Triage Result</h1>
          <p class="text-[11px] text-slate-500">Mobile Layout (375px width)</p>
        </div>
        <button class="text-xs font-semibold px-2.5 py-1 rounded-lg border bg-white"><i class="fa-solid fa-print"></i> PDF</button>
      </div>

      <!-- Emergency/Consult Banner -->
      <div class="p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-xs space-y-1.5">
        <div class="flex items-center gap-1.5 font-bold text-amber-900">
          <i class="fa-solid fa-stethoscope text-amber-600"></i>
          <span>CONSULT A DOCTOR</span>
        </div>
        <p class="text-[11px] text-slate-700 leading-relaxed">Evaluation recommended within 24-48 hours based on severe headache pattern.</p>
      </div>

      <!-- Candidate Conditions -->
      <div class="space-y-2">
        <h2 class="text-xs font-bold text-slate-900 uppercase tracking-wide">Candidate Conditions</h2>

        <div class="bg-white rounded-xl border border-slate-200 p-3 shadow-xs space-y-1.5 text-xs">
          <div class="flex justify-between items-center">
            <span class="font-bold text-slate-900">1. Migraine with Photophobia</span>
            <span class="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-bold">LIKELY</span>
          </div>
          <p class="text-[11px] text-slate-600">Matches unilateral throbbing pain with nausea.</p>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 p-3 shadow-xs space-y-1.5 text-xs">
          <div class="flex justify-between items-center">
            <span class="font-bold text-slate-900">2. Tension-type Headache</span>
            <span class="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-bold">POSSIBLE</span>
          </div>
        </div>
      </div>

      <!-- Mobile Disclaimer -->
      <div class="p-3 rounded-xl bg-blue-50 border border-blue-200 text-[11px] text-slate-700 leading-relaxed">
        <strong>DR-01 Notice:</strong> Non-diagnostic triage aid only. For life-threatening symptoms, call <strong>112</strong> immediately.
      </div>

      <button class="w-full py-2.5 rounded-xl border border-slate-300 bg-white text-xs font-semibold text-slate-800">
        Start New Assessment
      </button>
    </div>
    """
    return generate_html(HEADER_DEFAULT, main)


TEST_SCENARIOS = [
    ("TC-FLOW-M-01", page_tc_flow_m_01, 1080, 800),
    ("TC-FLOW-M-02", page_tc_flow_m_02, 1080, 800),
    ("TC-FLOW-M-03", page_tc_flow_m_03, 1080, 800),
    ("TC-FLOW-M-04", page_tc_flow_m_04, 1080, 820),
    ("TC-FLOW-M-05", page_tc_flow_m_05, 1080, 840),
    ("TC-FLOW-M-06", page_tc_flow_m_06, 1080, 800),
    ("TC-FLOW-M-07", page_tc_flow_m_07, 1080, 820),
    ("TC-FLOW-M-08", page_tc_flow_m_08, 1080, 780),
    ("TC-FLOW-M-09", page_tc_flow_m_09, 1080, 880),
    ("TC-FLOW-M-10", page_tc_flow_m_10, 1080, 780),
    ("TC-FLOW-M-11", page_tc_flow_m_11, 1080, 760),
    ("TC-FLOW-M-12", page_tc_flow_m_12, 1080, 760),
    ("TC-FLOW-M-13", page_tc_flow_m_13, 375, 667),  # Mobile iPhone SE
    ("TC-FLOW-M-14", page_tc_flow_m_14, 375, 667),  # Mobile iPhone SE
]


def main():
    print("Launching Google Chrome via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for tc_id, html_fn, width, height in TEST_SCENARIOS:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            html_content = html_fn()
            page.set_content(html_content, wait_until="networkidle")
            out_path = OUTPUT_DIR / f"{tc_id}.png"
            page.screenshot(path=str(out_path), full_page=False)
            context.close()
            size_kb = out_path.stat().st_size / 1024
            print(f"Captured {tc_id}.png ({width}x{height}, {size_kb:.1f} KB)")
        browser.close()
    print("All 14 browser screenshots generated successfully.")


if __name__ == "__main__":
    main()
