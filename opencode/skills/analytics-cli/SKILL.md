---
name: analytics-cli
description: Use for Datadog, Pup, PostHog, analytics, observability, metrics, logs, traces, dashboards, or event investigations; provides safe CLI guidance for read-only inspection and approved mutations.
---

# Analytics CLI

Use this skill for Datadog and PostHog analytics or observability investigations.
Use the Datadog Pup CLI as `pup` and the PostHog CLI as `posthog-cli` when they
are available in the environment.

## Datadog Pup

- Use `pup` directly in non-agent, read-only mode by default:
  `pup --no-agent --read-only ...`.
- `pup --no-agent auth status` is a safe authentication-status command and may
  be run without additional approval.
- Never use or permit a Pup command that lacks `--no-agent`.
- Treat any command that could mutate or destroy data as requiring explicit
  user approval before execution, even if it appears related to an
  investigation.
- Do not print authentication tokens, credentials, or secret-bearing debug
  output. Avoid returning sensitive resource payloads unless the user
  explicitly requests that data.

## PostHog

- Require explicit user approval before every `posthog-cli` command. No global
  read-only enforcement has been established for this CLI.
- Do not output credentials, tokens, or other credential-bearing diagnostics.
- Avoid returning sensitive resource payloads unless the user explicitly
  requests that data.

When approval is required, explain the command's intended effect and wait for
the user's explicit approval before running it.
