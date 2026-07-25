# Security policy

## Supported versions

Bowerbird is currently pre-1.0. Security fixes are made on the default branch
and included in the next release. The current `main` branch is supported. When
tagged releases are available, only the latest release is supported; older
commits and releases are not.

## Report a vulnerability privately

Do not open a public issue, discussion, or pull request for a suspected
vulnerability.

Use GitHub's private vulnerability reporting for this repository:

https://github.com/sergedoub/bowerbird/security/advisories/new

Include:

- the affected component and version or commit;
- the security impact and a realistic attack scenario;
- steps to reproduce or a minimal proof of concept; and
- any suggested mitigation, if known.

Do not include real access tokens, private knowledge-base content, or other
people's data. Use redacted or synthetic examples.

The maintainer aims to acknowledge a report within 3 business days and provide
an initial assessment within 7 business days. Fix and disclosure timing depends
on severity and complexity. Please allow time for a coordinated fix before
publishing details.

## Scope

Security reports are welcome for:

- Bowerbird source code and command-line tools;
- reusable GitHub Actions workflows shipped by this repository;
- authentication, token storage, and secret-handling behavior;
- repository-boundary controls intended to protect the public source repo;
- unsafe handling of untrusted content; and
- vulnerabilities that could expose, corrupt, or modify instance data.

The following are outside this project's security scope unless the issue is
caused by Bowerbird itself:

- X, GitHub, Slack, model providers, and other third-party services;
- leaked credentials already committed or exposed by an instance owner;
- the contents, configuration, access controls, or availability of a user's
  private Bowerbird instance;
- social engineering, spam, and denial-of-service reports without a concrete
  Bowerbird vulnerability; and
- reports produced only by an automated scanner with no reproducible impact.

## Public source and private instances

This repository is the public Bowerbird source. A personal Bowerbird instance
is a separate private repository that can contain credentials, raw source
material, compiled notes, and delivery configuration. Instance owners are
responsible for their repository visibility, collaborators, secrets, workflow
permissions, logs, and third-party accounts.

If a report concerns a private instance, first determine whether the cause is a
reusable Bowerbird source or workflow defect. Report that defect here using
redacted data. Do not grant the maintainer access to a private instance or send
its credentials.
