/**
 * @file PR policy checker, run by .github/workflows/pr-policy.yml through actions/github-script.
 *
 * Enforces the team workflow from CONTRIBUTING.md on every pull request:
 *   1. Feature PRs target `develop`. Only `develop` -> `main` release PRs may target `main`.
 *   2. The author is a registered team member (.github/team.json).
 *   3. Branch name is `<member-name>/<issue-no>-<kebab-desc>` and uses the author's own name.
 *   4. The PR title and every commit message follow Conventional Commits.
 *   5. The body links the branch's issue ("Closes #N"), and that issue is open,
 *      assigned to the author, and placed in a sprint milestone.
 *   6. Every checklist item in the PR body is ticked.
 *   7. One feature at a time: the author has no other open PR.
 *
 * The workflow checks out the BASE branch before running this file, so a PR
 * cannot weaken the policy that is judging it.
 */

const fs = require('fs');
const path = require('path');

/** Conventional Commit header: `type(optional-scope)!: summary` (summary 4-72 chars). */
const CONVENTIONAL = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9-]+\))?!?: \S.{3,71}$/;

/** Branch format `<name>/<issue-no>-<kebab-case-description>`. Group 1 = name, group 2 = issue number. */
const BRANCH = /^([a-z]+)\/(\d+)-[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** GitHub closing keyword followed by an issue reference. Group 1 = issue number. */
const ISSUE_LINK = /\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b/i;

/** PRs larger than this (added + deleted lines) get a warning asking to split them. */
const LARGE_PR_LINES = 800;

/**
 * Loads the login -> member map from .github/team.json.
 * @returns {Record<string, {name: string, role: string}>} Map keyed by lowercase GitHub login.
 */
function loadTeam() {
  const file = path.join(process.env.GITHUB_WORKSPACE || '.', '.github', 'team.json');
  const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  delete raw._comment;
  return raw;
}

/**
 * Entry point called by actions/github-script.
 * Collects every violation first, then fails once, so authors can fix everything in one pass.
 * @param {{github: object, context: object, core: object}} tools Objects injected by github-script.
 * @returns {Promise<void>}
 */
module.exports = async ({ github, context, core }) => {
  const pr = context.payload.pull_request;
  const { owner, repo } = context.repo;
  const author = pr.user.login;
  const errors = [];
  const warnings = [];

  // Bots (Dependabot) do not follow the member workflow.
  if (pr.user.type === 'Bot') {
    core.info(`Bot PR by ${author}: policy skipped.`);
    return;
  }

  // Sprint release PR opened by the leader: develop -> main. Only the title is checked.
  if (pr.base.ref === 'main') {
    if (pr.head.ref !== 'develop') {
      core.setFailed('Only `develop` may be merged into `main`. Re-target this PR to `develop`.');
    } else if (!CONVENTIONAL.test(pr.title)) {
      core.setFailed(`Release PR title must be a Conventional Commit, e.g. "chore(release): sprint 1".`);
    }
    return;
  }

  if (pr.base.ref !== 'develop') {
    errors.push(`PR targets \`${pr.base.ref}\`. Feature PRs must target \`develop\`.`);
  }

  // Rule 2: registered team member.
  const team = loadTeam();
  const member = team[author.toLowerCase()];
  if (!member) {
    errors.push(`@${author} is not listed in .github/team.json. Ask the team leader to add you.`);
  }

  // Rule 3: branch name, and the branch belongs to its author.
  const branch = pr.head.ref;
  const branchMatch = BRANCH.exec(branch);
  let branchIssue = null;
  if (!branchMatch) {
    errors.push(`Branch \`${branch}\` must look like \`<your-name>/<issue-no>-<short-desc>\`, e.g. \`vivek/12-chat-bubbles\`.`);
  } else {
    branchIssue = Number(branchMatch[2]);
    if (member && branchMatch[1] !== member.name) {
      errors.push(`Branch prefix \`${branchMatch[1]}/\` does not match your team name \`${member.name}/\`. Work only on your own branches.`);
    }
  }

  // Rule 4a: PR title.
  if (!CONVENTIONAL.test(pr.title)) {
    errors.push(`PR title "${pr.title}" must follow Conventional Commits: \`type(scope): summary\`, e.g. \`feat(chat): render message bubbles\`.`);
  }

  // Rule 5: linked issue.
  const body = pr.body || '';
  const linkMatch = ISSUE_LINK.exec(body);
  if (!linkMatch) {
    errors.push('PR body must contain `Closes #<issue-number>`.');
  } else {
    const linked = Number(linkMatch[1]);
    if (branchIssue !== null && linked !== branchIssue) {
      errors.push(`Body closes #${linked} but the branch is for issue #${branchIssue}. They must match.`);
    }
    try {
      const { data: issue } = await github.rest.issues.get({ owner, repo, issue_number: linked });
      if (issue.pull_request) {
        errors.push(`#${linked} is a pull request, not an issue.`);
      } else {
        if (issue.state !== 'open') errors.push(`Issue #${linked} is closed. Link an open issue.`);
        const assignees = (issue.assignees || []).map((a) => a.login.toLowerCase());
        if (!assignees.includes(author.toLowerCase())) {
          errors.push(`Issue #${linked} is not assigned to @${author}. Only work on issues assigned to you.`);
        }
        if (!issue.milestone) errors.push(`Issue #${linked} has no sprint milestone. Ask the leader to add one.`);
      }
    } catch (err) {
      errors.push(`Issue #${linked} could not be read (${err.status || err.message}).`);
    }
  }

  // Rule 6: all checklist boxes ticked.
  const unticked = body.split('\n').filter((line) => /^\s*[-*]\s+\[ \]/.test(line));
  if (unticked.length > 0) {
    errors.push(`${unticked.length} checklist item(s) are not ticked. If an item does not apply, tick it and add "N/A" after it.`);
  }

  // Rule 7: one feature at a time.
  const openPrs = await github.paginate(github.rest.pulls.list, { owner, repo, state: 'open', per_page: 100 });
  // Release PRs (develop -> main) are not features, so they do not count.
  const others = openPrs.filter((p) => p.user.login === author && p.number !== pr.number && p.base.ref === 'develop');
  if (others.length > 0) {
    const list = others.map((p) => `#${p.number}`).join(', ');
    errors.push(`One feature at a time: @${author} already has open PR(s) ${list}. Get those merged or closed first, then re-run this check.`);
  }

  // Rule 4b: every commit message. Also warn about commits that will not count toward the author's stats.
  const commits = await github.paginate(github.rest.pulls.listCommits, { owner, repo, pull_number: pr.number, per_page: 100 });
  for (const c of commits) {
    const header = c.commit.message.split('\n')[0];
    const sha = c.sha.slice(0, 7);
    if (c.parents.length > 1 || header.startsWith('Merge ')) continue; // "Update branch" merges are fine.
    if (!CONVENTIONAL.test(header)) {
      errors.push(`Commit ${sha} "${header}" is not a Conventional Commit. Fix it with \`git rebase -i\` or \`git commit --amend\`.`);
    }
    if (!c.author) {
      warnings.push(`Commit ${sha} uses an email that is not linked to any GitHub account, so it will not count in your contribution stats. Run \`git config user.email <your GitHub email>\`.`);
    } else if (c.author.login !== author) {
      warnings.push(`Commit ${sha} was authored by @${c.author.login}, not @${author}.`);
    }
  }

  if (pr.additions + pr.deletions > LARGE_PR_LINES) {
    warnings.push(`This PR changes ${pr.additions + pr.deletions} lines. PRs over ${LARGE_PR_LINES} lines are hard to review, so consider splitting it.`);
  }

  // Report.
  await core.summary
    .addHeading('PR policy', 2)
    .addRaw(errors.length ? `❌ ${errors.length} problem(s) to fix:` : '✅ All policy checks passed.', true)
    .addList(errors)
    .addRaw(warnings.length ? '⚠️ Warnings:' : '', true)
    .addList(warnings)
    .write();

  warnings.forEach((w) => core.warning(w));
  if (errors.length) {
    errors.forEach((e) => core.error(e));
    core.setFailed(`${errors.length} PR policy violation(s). See the job summary. Rules are in CONTRIBUTING.md.`);
  }
};
