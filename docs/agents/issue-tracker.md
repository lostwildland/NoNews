# Issue tracker: GitHub

Issues and specs live in `lostwildland/NoNews`.
Use the `gh` CLI. Explicitly pass `--repo lostwildland/NoNews`
for issue commands; use `repos/lostwildland/NoNews` for API paths.
The NetNewsWire upstream is not this project's tracker.

## Operations

- Create: `gh issue create --repo lostwildland/NoNews --title "..." --body-file <file>`
- Read: `gh issue view <number> --repo lostwildland/NoNews --json number,title,body,labels,assignees,comments`
- List: `gh issue list --repo lostwildland/NoNews --state open`
  with appropriate label filters and pagination when completeness matters.
- Comment: `gh issue comment <number> --repo lostwildland/NoNews --body-file <file>`
- Update: `gh issue edit <number> --repo lostwildland/NoNews`
- Close: `gh issue close <number> --repo lostwildland/NoNews`

Use UTF-8 body files for multiline descriptions and comments.
“Publish to the issue tracker” means create an issue.
“Fetch the relevant ticket” means read its body and comments.

## Pull requests as a triage surface

PRs as a request surface: no.

## Wayfinding operations

- Map: one issue labelled `wayfinder:map`.
- Tickets: GitHub sub-issues of the map, labelled exactly one of
  `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`,
  or `wayfinder:task`. Use only wayfinder labels on maps and tickets.
- Parent relationship: use native sub-issues through `gh` or the
  GitHub API. The API's `sub_issue_id` is the child's database ID.
- Blocking: use native issue dependencies:
  POST `repos/lostwildland/NoNews/issues/<child>/dependencies/blocked_by`
  with `issue_id` set to the blocker's numeric database ID.
  Obtain it from the issue API's `id`, not its number or node_id.
- Frontier: query the map's children; select open, unassigned tickets
  with no open blockers, in the map's sub-issue order.
- Claim: assign the selected ticket to the driving developer before work.
- Resolve: post a resolution comment, close the ticket, then append
  its linked title and a one-line gist to the map's Decisions so far.
- Refer to maps and tickets by linked title in human-facing text.

If native sub-issues are unavailable, use a task list in the map
and `Part of #<map>` in each child. If native dependencies are
unavailable, use `Blocked by: #<number>` and check each blocker's state.
