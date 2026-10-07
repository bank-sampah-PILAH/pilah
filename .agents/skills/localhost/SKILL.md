---
name: localhost
description: Copy local-only environment and Firebase config from canonical PILAH checkouts into a designated sibling worktree.
disable-model-invocation: true
---

# localhost

Copy ignored local configuration into one explicit PILAH sibling worktree. From the workspace root:

```bash
python3 .agents/skills/localhost/scripts/copy_config.py --target pilah-be-worktrees/feature-pil-334
python3 .agents/skills/localhost/scripts/copy_config.py --target pilah-mobile-worktrees/feature-pil-344
```

From a target worktree root, run `python3 ../../.agents/skills/localhost/scripts/copy_config.py` to target the current worktree.

The backend target receives `pilah-be/.env`. The mobile target receives `pilah-mobile/.env` and `pilah-mobile/android/app/google-services.json`.

The helper verifies the canonical source and sibling-worktree target, confirms each destination is git-ignored, and writes files with mode `0600`. Identical files are left in place. A different existing destination is preserved and reported; use `--replace` only when the user explicitly requests replacing its local configuration. It never prints file contents.

After copying, check backend database settings without displaying credentials before starting it; use a scratch local database for web testing. The mobile `google-services.json` is for Android/Firebase, not required by web Google Sign-In. For real web OAuth, backend `GOOGLE_CLIENT_ID` must match mobile `GOOGLE_SERVER_CLIENT_ID`, and the OAuth client must authorize the local web origin.
