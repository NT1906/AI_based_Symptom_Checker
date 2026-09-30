/**
 * @file Documentation gate, run by .github/workflows/ci.yml on pull requests.
 *
 * Every source file added or modified in the PR must start with a header comment
 * explaining what the file is for (AI_RULES.md §5):
 *   - TypeScript / JavaScript: a block comment containing `@file` within the first 20 lines.
 *   - Python: a module docstring as the first statement.
 *
 * Usage: node .github/scripts/check-file-headers.js <base-ref>   e.g. origin/develop
 */

const { execSync } = require('child_process');
const fs = require('fs');

/** Only application code is checked. Config, generated code and migrations are exempt. */
const SOURCE_DIRS = /^(client\/src|server\/src|server\/prisma\/seed|shared|ai|tests)\//;
const SOURCE_EXT = /\.(ts|tsx|js|jsx|mjs|cjs|py)$/;
const EXEMPT = /(\.d\.ts$|\.config\.|\/migrations\/|\/generated\/|__init__\.py$)/;

/** How many leading lines may come before the `@file` tag in JS/TS files. */
const HEADER_WINDOW = 20;

/**
 * Lists files added or modified between the base ref and HEAD.
 * @param {string} baseRef Git ref to compare against, e.g. `origin/develop`.
 * @returns {string[]} Repository-relative file paths.
 */
function changedFiles(baseRef) {
  const out = execSync(`git diff --name-only --diff-filter=AM ${baseRef}...HEAD`, { encoding: 'utf8' });
  return out.split('\n').filter(Boolean);
}

/**
 * Checks whether a file starts with the required header.
 * @param {string} file Repository-relative path.
 * @returns {boolean} True when the header is present.
 */
function hasHeader(file) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  if (file.endsWith('.py')) {
    // Skip shebang, encoding line, comments and blank lines; the first real statement must be a docstring.
    const first = lines.find((l) => l.trim() && !l.trim().startsWith('#'));
    return Boolean(first) && /^\s*[rRuU]?("""|''')/.test(first);
  }
  return lines.slice(0, HEADER_WINDOW).some((l) => l.includes('@file'));
}

const baseRef = process.argv[2] || 'origin/develop';
const missing = changedFiles(baseRef)
  .filter((f) => SOURCE_DIRS.test(f) && SOURCE_EXT.test(f) && !EXEMPT.test(f) && fs.existsSync(f))
  .filter((f) => !hasHeader(f));

if (missing.length) {
  console.error('These files are missing the required header comment (see AI_RULES.md §5):');
  missing.forEach((f) => console.error(`::error file=${f},line=1::Missing file header (@file block or Python module docstring)`));
  process.exit(1);
}
console.log('All changed source files have a header comment.');
