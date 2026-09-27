# AI-Based Symptom Checker — Project Overview

## Project Description

The AI-Based Symptom Checker is a conversational health-guidance tool that helps users understand what might be causing their symptoms and how urgently they should act on it. Rather than presenting a traditional multi-field medical intake form, the entire experience runs as a guided chat — the user describes what they're feeling in plain language, optionally attaches a photo of a visible symptom, and the system responds step by step: confirming what it understood, asking a clarifying question or two if needed, and finally presenting its assessment.

The assessment itself has two parts. First, the system identifies the most likely conditions matching the reported symptoms and shows how confident it is in each. Second, it translates that into a risk level — telling the user not just "what this might be" but "how seriously should I take this." Low-risk outcomes come with general self-care pointers; higher-risk outcomes point the user toward finding the right kind of doctor nearby, without the system itself acting as a booking service or medical authority.

This tool is explicitly positioned as an **informational triage aid, not a diagnostic or prescribing authority**. It does not replace a doctor, does not issue prescriptions, does not manage appointments, and does not maintain any relationship with healthcare providers beyond pointing users toward one when appropriate. This boundary is intentional and shapes every feature below — the system's job ends at "here's what this might be and here's what to do next," and a licensed professional takes over from there.

The target users are anyone experiencing symptoms who wants a fast, low-friction first read on whether something is minor or worth seeing a doctor about — before deciding whether a clinic visit is necessary.

---

## Features

### 1. Guided chat interface
Instead of a form with multiple sections (symptom fields, severity dropdowns, duration pickers, etc.), the user experiences the whole assessment as a single ongoing conversation. Each piece of information is requested one at a time, in context, the way a person would naturally describe their situation to another person. This matters because health-related forms tend to feel clinical and effortful — a conversation feels lower-stakes and easier to start, even though it's collecting the same information underneath. The user always knows what's being asked of them at each moment, and never has to view or fill out a long page of fields at once.

### 2. Text-based symptom entry
The starting point of every assessment is the user typing, in their own words, what they're experiencing — no dropdowns, no pre-set checklists to scroll through first. This respects that most people don't think of their symptoms in clinical terms ("I've felt gross and achy since yesterday" rather than "myalgia, malaise, onset 24h"), and the system is expected to work with that kind of natural description rather than forcing the user to translate it into medical vocabulary themselves.

### 3. Optional image upload
For conditions that are visibly identifiable — rashes, skin discoloration, swelling, bumps, and similar external symptoms — the user can attach a photo to support or replace a text description. This is presented as optional and situational: it's offered when the symptoms described suggest a visual component would help, not as a default input option sitting next to the text box for every kind of complaint. The system is upfront that this only applies to visibly assessable conditions, not general symptoms like fatigue or headache.

### 4. Symptom confirmation and editing
Before any analysis happens, the bot reflects back what it believes the user described — a short summary or list of symptoms — and gives the user a direct chance to correct it: add something missed, remove something misunderstood, or adjust a detail. This step exists because natural-language input can be misread, and the user is the only one who can verify it was understood correctly. It's the single most important trust-building step in the flow, since everything downstream (the prediction, the risk level, the recommendation) depends on this being accurate.

### 5. Clarifying follow-up questions
When the symptoms given aren't specific enough to produce a confident result, the bot doesn't guess — it asks a small number of targeted questions to fill the gap (for example, asking about duration, associated symptoms, or severity). This mirrors how an actual triage conversation works: a nurse or doctor rarely reaches a conclusion from the first sentence a patient says, they ask one or two follow-ups. The number of follow-ups is intentionally capped at two or three, so the conversation stays quick and doesn't feel like an interrogation — if the system still isn't confident after that, it errs toward caution in the final risk assessment rather than continuing to ask.

### 6. Condition prediction with confidence level
Once enough information is gathered, the system presents the two or three most likely conditions matching what was described, each labeled with a plain-language confidence level such as "Likely," "Possible," or "Less likely." This is deliberately not shown as a bare statistic (like "73%") — a number like that implies a precision and authority the system shouldn't claim, and can be misread as more certain than it is. The qualitative framing communicates the same relative confidence without overstating it.

### 7. Risk-level assessment
Alongside the possible conditions, every result carries a risk classification — self-care, consult a doctor, or seek urgent/emergency care. This is arguably the most important output of the whole system, because most users care less about the exact name of a condition and more about "do I need to do something about this, and how soon." The three-tier structure avoids a false binary (just "fine" vs. "not fine") and gives space for the common middle case — not an emergency, but worth getting checked. When the system isn't confident in its prediction, the risk level defaults upward rather than downward, so uncertainty never quietly gets treated as "probably nothing."

### 8. Self-care guidance (low risk)
When the assessed risk is low, the user receives general, everyday self-care suggestions relevant to the likely condition — things like rest, hydration, or common non-prescription approaches. This is intentionally framed as general guidance and explicitly not a prescription or medical instruction, both in language and in tone, to avoid implying a level of medical authority the system doesn't have. The goal is to give the user something useful to do immediately, without overstepping into territory that belongs to an actual clinician.

### 9. Doctor referral via map (high risk)
When the assessed risk is elevated, instead of leaving the user with just a warning, the system identifies the type of specialist relevant to the likely condition and gives them a direct way to search for nearby options of that specialty through an external map/search service. This closes the loop from "something may be wrong" to "here's a concrete next step," without the system taking on the responsibility of vetting, listing, or managing actual healthcare providers. The referral is a pointer outward, not a service the system owns or operates — no doctor profile, availability calendar, or booking exists inside the product.

### 10. Guest mode with optional account
Anyone can complete a full assessment without signing up first — this keeps the barrier to getting an answer as low as possible, which matters for a tool people may reach for when they're not feeling well and don't want friction. Creating an account is entirely optional and only adds value for users who want their past assessments remembered for next time. When an account is created, the information collected is deliberately minimal — basic details like age, sex, and any existing chronic conditions the user chooses to share — kept only insofar as it improves how future assessments are interpreted, not as a general medical profile.

### 11. Restart / repeat assessment
At any point, the user can start a new assessment from scratch — useful if they want to check a different symptom, if they made an early mistake, or if their situation has changed. This is offered as a simple, always-available option so users never feel stuck partway through a flow that no longer matches what they meant to ask about.

### 12. Privacy and consent
Because the system deals with personal health information, users are shown a clear, plain-language consent step before anything is stored — explaining what is being kept and why, before it happens rather than after. Data handling follows applicable privacy regulations for personal health information. This is treated as a first-class feature rather than a legal footnote, since trust in how personal health details are handled directly affects whether users are willing to be honest and complete in what they share.

---

## Explicitly Out of Scope

These were considered during planning and deliberately excluded, to keep the product's responsibilities clear and its scope honest:

- **Appointment booking or scheduling with doctors** — the system refers users outward; it does not manage or facilitate the actual appointment.
- **Doctor accounts, doctor dashboard, or any doctor-side data** — there is no login, profile, or interface for healthcare providers anywhere in the system; doctors are never a stakeholder inside the product.
- **Doctor ratings, reviews, or availability tracking** — the system does not maintain any ongoing information about real providers, which avoids the burden (and liability) of keeping such data accurate and current.
- **General open-topic chatbot conversation** — the chat interface exists solely to run the symptom-assessment flow; it is not a general-purpose assistant and does not entertain unrelated questions or requests.
- **Any form of medical diagnosis, prescription, or treatment authorization** — everything the system outputs is framed as informational guidance, never as a clinical diagnosis or an instruction to take a specific treatment. That judgment always remains with an actual healthcare professional.