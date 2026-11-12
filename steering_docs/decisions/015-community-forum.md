# Decision 015: Community forum storage and deletion

## Context

Signed-in members need to share questions, discussions, and portfolio posts with threaded replies. Community author identity must not copy email addresses or Clerk subjects into forum records.

## Decision

Store categories, posts, and replies in separate tables. The user row stores the public name and optional avatar once. Posts and replies reference their author with `ON DELETE SET NULL`, so account deletion removes the profile link but keeps written content. The API displays `Member` for an anonymized post.

Replies point to a parent with a composite `(post_id, parent_reply_id)` foreign key. This prevents a reply from pointing into another post. The API does not accept parent changes, so it cannot make cycles. Deleting a post cascades through its replies. Deleting one reply replaces its body with a tombstone and preserves its position in the thread.

List posts newest first and direct-child replies oldest first. Use keyset cursors bound to the exact query scope. The API returns one sibling page at a time and does not build the full reply tree.

## Consequences

- The database protects thread ownership if an application write is incorrect.
- Account deletion anonymizes authors without deleting their contributions.
- A tombstone hides the original reply text and author but keeps descendant replies readable.
- Clients request each reply level separately and can paginate large sibling lists.
- Optional signed Clerk `name` and `picture` claims provide public profile values. Existing tokens without these claims remain valid.
