# config/

Business rules the workflows read at run time. Mounted read-only into n8n at
`/home/node/.n8n-files/config`; edit a file and the next execution uses it.

| File | Milestone | Purpose |
|---|---|---|
| `icp.json` | M3 | Ideal-customer-profile criteria, weights, rating guides, tier thresholds, free-mail domains, spam rules. |
| `reply_style.md` | M4 | Tone, structure, sign-off, booking-link placeholder and forbidden claims for reply drafts. |
