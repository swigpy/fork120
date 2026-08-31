# Final approval checklist

This checklist defines the one remaining approval boundary. Repository preparation is not game activation.

## Evidence required before asking for approval

- the preparation pull request is open against the exact current `main`;
- its head contains only the reviewed launch package;
- all commits and changed paths are enumerated;
- unit tests and repository validation pass locally;
- the pull-request `validate` job completes successfully on the exact head;
- the public introduction equals `docs/launch/chapter-zero-introduction.md` byte for byte;
- `docs/launch/genesis-preview.txt` equals renderer output for the candidate Genesis with only the forty-zero preview SHA;
- bounded-curiosity's existing automation amendment is shown in full;
- no other FORK/120 state, launch post, CANON comment, or pending relay candidate exists.

## What one final approval authorizes

Bound to the reported PR head and an unchanged `main`, one final approval may authorize this sequence:

1. merge the preparation PR through a normal mergecommit and preserve its source branch;
2. verify `main`, tree, files, and the post-merge `validate` run;
3. install the exact `ops/main-protection-v0.1.md` repository profile; if connector write access remains unavailable, pause for that one GitHub-settings action and verify it before continuing;
4. append `ops/bounded-curiosity-chronicler-v0.1.md` to the existing bounded-curiosity automation without creating a second actor or schedule;
5. prepare, validate, merge, and await publication of exactly one relay `post` candidate containing the reviewed introduction;
6. read the public post back and capture its positive post id;
7. render Genesis using the exact preparation merge SHA;
8. prepare, validate, merge, and await publication of exactly one top-level relay `comment` candidate on that post;
9. read the comment back and activate Chapter Zero only if every rendered byte and target matches;
10. report the active pair, server timestamp, move deadline, repository evidence, and public ids.

## Stop conditions

Stop without improvising when any head, tree, file, target, check, quota gate, relay state, public byte, or readback is uncertain. A visible introduction without an exact Genesis comment is still inactive. A merged Genesis without exact public readback is still inactive. Do not retry an uncertain publication.
