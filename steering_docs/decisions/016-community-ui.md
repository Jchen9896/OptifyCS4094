# Decision 016. Community UI

## Goal

Signed-in members can browse, create, edit and discuss Community posts in the existing Optify design. This work does not add voting, search, uploads, portfolio snapshots or RAG.

## Routes and ownership

Use three routes inside the existing authentication and application shell:

- `/community` lists posts. The category is in the query string.
- `/community/new` owns a new-post draft.
- `/community/:postId` owns one authoritative post and its root reply list.

Each lazy reply list owns one direct-child sibling sequence and cursor. Each reply node owns its expansion and edit state. Only expanded branches fetch children. Visual indentation stops after three levels, but the lazy hierarchy has no depth limit. There is no global normalized thread store.

A successful mutation invalidates older reads and applies its authoritative response without remounting other reply drafts. A successful reply delete immediately hides the original text and author using the documented delete semantics. Descendants remain mounted. A later sibling read obtains the server tombstone. No deletion timestamp is invented.

## Network and session boundary

Zod parses unknown JSON and supplies the wire-aligned types. Live and deleted reply variants have distinct body and author shapes. Strict null checking preserves those variants during compilation.

The API client acquires the current Clerk token for every request. It never sends author fields. Post payloads explicitly select title, body and category, including when the input came from a full post response.

The client lifetime is keyed to both account and Clerk session. Request abort signals and local ownership checks reject stale completions. A 401 stops further requests until reauthentication. Reads can retry. Writes do not retry automatically because an interrupted or invalid-response write can have completed.

## Rendering and drafts

Use the same CommonMark renderer in previews, feed excerpts, posts and replies. Raw HTML and Markdown images are disabled. The URL policy rejects script, data and protocol-relative schemes. Code blocks scroll inside their available width.

Drafts remain in component memory after failed writes. They are not stored across accounts. Known links, Cancel, account actions and invalid-cursor reload warn before disposal. Browser unload uses the browser warning. This is not a universal blocker for browser Back, account changes or external navigation.

Delete dialogs focus Cancel first and restore the trigger on ordinary closure. Reply deletion focuses the surviving Reply action when its delete trigger disappears.

The responsive shell change applies only to Community below 1024 pixels. Desktop navigation, onboarding and other route layouts stay unchanged.

## Migration integration

Onboarding revision `20261111_0007` and Community revision `20261112_0007` share parent `20261111_0006`. Revision `20261112_0008` joins both heads without schema operations. Neither applied revision is renamed or removed. Upgrading the existing isolated Community database preserves its revision and adds onboarding before joining the heads.

## Verification boundary

`frontend/tests/community/README.md` contains commands and browser checks. The separate fixture Vite config injects fixture clients and aliases Clerk only for the harness. It blocks the normal application entry. The production build does not include the fixture entry or alias.

Fixture checks prove component behavior, not live authentication. The normal app was observed redirecting an unsigned browser to the real Clerk login. Authenticated end-to-end verification still needs an authorized signed-in test account. Backend permissions remain covered by the isolated backend suite.
