/**
 * @file Contribution report, run by .github/workflows/contribution-report.yml.
 *
 * Counts non-merge commits on `develop` and merged PRs per team member since the
 * project start date, then writes a table to the workflow job summary. Members
 * below 75% of the team median are flagged so the leader can rebalance work early.
 */

const fs = require('fs');
const path = require('path');

/** Members under this fraction of the median commit count are flagged. */
const LOW_SHARE = 0.75;

/**
 * Returns the median of a list of numbers.
 * @param {number[]} values Numbers to summarise.
 * @returns {number} The median, or 0 for an empty list.
 */
function median(values) {
  if (!values.length) return 0;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/**
 * Entry point called by actions/github-script.
 * @param {{github: object, context: object, core: object}} tools Objects injected by github-script.
 * @returns {Promise<void>}
 */
module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo;
  const since = process.env.PROJECT_START || '2026-10-10T00:00:00Z';
  const branch = process.env.REPORT_BRANCH || 'develop';

  const team = JSON.parse(fs.readFileSync(path.join(process.env.GITHUB_WORKSPACE, '.github', 'team.json'), 'utf8'));
  delete team._comment;

  const stats = {};
  for (const login of Object.keys(team)) stats[login] = { commits: 0, prs: 0 };
  const unlinked = {};

  // Non-merge commits on the integration branch. Squash is disabled, so each member's commits survive.
  const commits = await github.paginate(github.rest.repos.listCommits, { owner, repo, sha: branch, since, per_page: 100 });
  for (const c of commits) {
    if (c.parents.length > 1) continue;
    const login = c.author && c.author.login.toLowerCase();
    if (login && stats[login]) stats[login].commits += 1;
    else if (!login) unlinked[c.commit.author.email] = (unlinked[c.commit.author.email] || 0) + 1;
  }

  // Merged PRs into develop.
  const prs = await github.paginate(github.rest.pulls.list, { owner, repo, state: 'closed', base: branch, per_page: 100 });
  for (const p of prs) {
    const login = p.user.login.toLowerCase();
    if (p.merged_at && p.merged_at >= since && stats[login]) stats[login].prs += 1;
  }

  const med = median(Object.values(stats).map((s) => s.commits));
  const rows = Object.entries(stats)
    .sort((a, b) => b[1].commits - a[1].commits)
    .map(([login, s]) => {
      const share = med ? Math.round((s.commits / med) * 100) : 100;
      const flag = med && s.commits < med * LOW_SHARE ? '⚠️ below target' : '✅';
      return [team[login].name, `@${login}`, String(s.commits), String(s.prs), `${share}%`, flag];
    });

  const summary = core.summary
    .addHeading(`Contribution report: ${branch} since ${since.slice(0, 10)}`, 2)
    .addTable([
      [{ data: 'Member', header: true }, { data: 'GitHub', header: true }, { data: 'Commits', header: true },
       { data: 'Merged PRs', header: true }, { data: '% of median', header: true }, { data: 'Status', header: true }],
      ...rows,
    ])
    .addRaw(`Median commits: ${med}. Members under ${LOW_SHARE * 100}% of the median are flagged.`, true);

  if (Object.keys(unlinked).length) {
    summary.addHeading('Commits with unlinked emails (not counted)', 3)
      .addList(Object.entries(unlinked).map(([email, n]) => `${email}: ${n} commit(s)`));
  }
  await summary.write();
};
