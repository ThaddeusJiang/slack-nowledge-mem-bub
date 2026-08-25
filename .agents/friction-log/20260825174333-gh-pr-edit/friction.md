---
title: 'gh pr edit fails when projectCards deprecation is returned'
severity: 'minor'
target: 'cli/cli'
---

## Context

Updating pull request metadata with `gh pr edit 8` in this repository failed before applying the change.

## Friction

GitHub returned a GraphQL error stating that Projects (classic) is deprecated because `gh pr edit` queried `repository.pullRequest.projectCards`, even though only the PR title and body were being edited.

## Workaround

Use `gh api --method PATCH repos/{owner}/{repo}/pulls/{number}` with `title` and `body` fields.
