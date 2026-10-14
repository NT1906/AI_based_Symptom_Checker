# React + TypeScript + Vite

A **quick‑start template** for the AI‑Based Symptom Checker frontend. It bundles:

- **React 18** with TypeScript
- **Vite** for blazingly fast dev server & build
- **Tailwind CSS** for the UI design you just edited
- **Zustand & TanStack Query** for state & data fetching

---

## 📦 Prerequisites (Windows)

- **Node.js** ≥ 20 (recommended LTS) – install from https://nodejs.org
- **npm** (comes with Node) – verify with `npm -v`
- Git (already installed for the repo)

> **Tip:** Open PowerShell **as Administrator** the first time you run `npm install` so that global binaries are added to your `PATH` without permission issues.

---

## 🚀 Getting the project running locally

```powershell
# 1️⃣ Clone the repo (if you haven't already)
git clone https://github.com/NT1906/AI_based_Symptom_Checker.git
cd "AI Based SE project/client"

# 2️⃣ Install dependencies
npm ci   # deterministic install; use `npm install` if you prefer

# 3️⃣ (Optional) Copy environment variables
#    Create a .env file based on .env.example if the backend URL is needed
#    Example:
#    REACT_APP_API_BASE_URL=http://localhost:8000/api

# 4️⃣ Start the development server
npm run dev
```

The dev server will start at **http://localhost:5173** and automatically open your default browser. You should now see the brand‑new landing page, consent flow, and risk UI you just built.

---

## 📦 Build for production

```powershell
npm run build   # creates a `dist/` folder ready for deployment (Vercel, Render, etc.)
```

---

## 🧪 Running the test suite

```powershell
# Run all unit / integration tests
npm test

# If you encounter the Vitest pool‑timeout on Windows, run with a single worker:
VITEST_WORKERS=1 npm test -- --run
```

---

## 🔧 Linting & formatting

```powershell
npm run lint   # Oxc + Tailwind linting – will report errors / warnings
npm run format # (if a format script exists) – automatically format code
```

---

## 📚 Helpful links

- **Vite docs:** https://vitejs.dev/guide/
- **Tailwind CSS:** https://tailwindcss.com/docs
- **React docs:** https://react.dev/
- **Project board:** https://github.com/NT1906/AI_based_Symptom_Checker/projects

---

*Happy coding!* 🎉
