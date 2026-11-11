# Decision 011 - Authentication

Use Clerk email/password and Google sign-in for the class demo. The React client sends a Clerk session token in the `Authorization` header when saving or loading portfolios. FastAPI verifies its signature, issuer, expiry, and frontend origin before it resolves the Clerk subject to a local user UUID. Configure a custom `email` session claim from `{{user.primary_email_address}}` in the Clerk dashboard. Require verified email addresses in the Clerk application.

Guests can use stock search, price history, and optimization. Portfolio routes require a verified session. The API derives ownership from that session and never accepts a caller-supplied user ID. Existing portfolio UUID ownership is retained. A first sign-in creates a local user with `oauth_provider=clerk` and the verified subject. A conflicting email belonging to another identity must be resolved explicitly and must not transfer portfolios.

Use Clerk's development instance for the local Vite and Compose demo. Each review PR is based on the preceding auth branch. Merge PR #38 into main before merging the auth stack in order.
