# Remote CI registration investigation

Observed 2026-10-28 for `lostwildland/NoNews`. The repository is an active fork with admin access. Actions repository policy reports enabled/all actions; workflow-token defaults remain read-only. No permission expansion was made.

The default `main` points at `d9ec7df6f92c53dcd4bc0d9a26d14d9c0716bf8b`. Its `.github/workflows/ci.yml` is a regular 3,483-byte file, blob `f5187fe6a27e94fd0984a3851d21abafc7a0603a`. Ruby Psych parses its YAML. It declares `pull_request` without a branch filter and pushes to main; it has no scheduled trigger. The workflow list and run list nevertheless report zero, and retrieving `ci.yml` through the workflow endpoint returns 404. PR33 is draft and mergeable, with no checks.

The current official [runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) maps `macos-26` to arm64; its [arm64 image inventory](https://raw.githubusercontent.com/actions/runner-images/main/images/macos/macos-26-arm64-Readme.md) includes Xcode 26.6 at the configured path. Those do not explain the missing workflow registration. GitHub's [workflow-management documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows) documents disabled scheduled workflows on forks; that schedule-specific rule does not establish the cause of this pull-request case.

A separate [draft foundation PR34](https://github.com/lostwildland/NoNews/pull/34) now targets main with the already accepted T00/T01 source and planning records, without merging. Its head at creation is `4cf7ee15cece76e07597c7d3a922855b0408bc74`. The first post-create read still showed no check rollup, registered workflows or runs. This narrows the observations but does not prove a GitHub defect or a particular policy cause.

Local CI/native results retain their recorded source boundaries and do not become GitHub results. Remote CI remains unverified; source implementation can continue. No production data, signing credentials or additional repository permissions were used.
