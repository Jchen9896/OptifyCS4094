# Verify Community UI

## Component and boundary tests

From `frontend/`:

```sh
npm ci
npm run test:community
npx tsc -p tests/community/tsconfig.json
npm run build
node --test tests/onboarding/onboardingApi.test.ts
```

The Community tests use real components with injected HTTP fixtures. Deferred operations cover stale reads, pagination changes and unmounted writes. These tests do not prove a live Clerk session.

## Browser fixture

Use the separate fixture server, not the normal app server:

```sh
npm run dev:community-fixture
```

Open http://127.0.0.1:5175/tests/community/harness.html#/community.

The page has a visible fixture label. Its Vite config aliases Clerk only for this entry and blocks the normal app entry. The production build does not import this harness or alias. Fixture posts and replies exist only in memory and reset on page reload. No fixture request writes to PostgreSQL. Its fallback API proxy is explicitly port 8011.

Check these flows at desktop width, 390 pixels and 320 pixels:

1. Filter categories, load the next feed page, and open a post.
2. Confirm that long Markdown links wrap and code scrolls inside its block. The page must not scroll horizontally.
3. Create a post, preview Markdown, edit it, and save a reply.
4. Use **Fail next write** before saving. Confirm that the error warns about an uncertain write and retains the fields. Submit again only after checking the discussion.
5. Expand a reply branch. Add a nested reply, delete its parent, and confirm that the descendant remains visible.
6. Open a delete dialog with the keyboard. Cancel receives initial focus. Escape restores trigger focus. Successful reply deletion focuses the surviving Reply action.
7. Open the mobile navigation dialog. Confirm that all workspace and account actions remain present. Escape closes it and restores the menu trigger.
8. Use **Fail next read**, then change categories. Retry the failed list.

## Live Clerk boundary

For the normal app, stop the fixture server and run:

```sh
API_PROXY_TARGET=http://127.0.0.1:8011 npm run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Only use an API on port 8011 that was started with the explicit isolated Community database URL. The default development proxy remains unchanged for other developers.

Open `/community`. Without a signed-in account, the normal app redirects to the real Clerk login. A publishable key is not a signed-in session. Complete authenticated end-to-end checks only with an authorized test account. Do not add a production bypass.

Drafts stay in component memory. Explicit links, Cancel, account menu actions and invalid-cursor reload warn before disposal. Browser unload uses the browser warning. This is not a universal SPA blocker for browser Back or external session changes.
