# Main protection profile v0.1

**Status: proposed post-merge repository setting. This document does not apply GitHub settings.**

Apply one active branch ruleset named `fork120-main` to the default branch only.

## Required rules

- restrict deletions;
- block non-fast-forward updates;
- require changes through a pull request;
- require zero approving reviews for Chapter Zero, so bounded-curiosity's fully mechanical state PR is not dependent on another actor;
- require the status check named exactly `validate`;
- require the branch to be current before merge;
- allow no bypass actor for normal operation.

Do not require signed commits in v0.1 because the current connector-created commits are unsigned. Do not require deployments or code-owner review. Human review remains mandatory for rules, licenses, workflows, Story Bible, region, or operational-scope changes through the separate approval process; automated zero-review merge authority is limited by the Chronicler amendment to next-state and ledger paths.

## Verification

Before launch, read the server-owned ruleset back and verify:

- enforcement is active;
- target is the default branch only;
- deletion and non-fast-forward rules are present;
- pull requests are required;
- `validate` is the required strict status check;
- no unexpected bypass or extra rule exists.

The available GitHub connector currently exposes ruleset reads but not ruleset writes. If that remains true after the preparation merge, Chapter Zero stays inactive until this exact profile is applied through GitHub settings and read back successfully.
