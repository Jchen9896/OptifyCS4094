# Decision 014 - Risk profile onboarding

Ask the user a short questionnaire for each portfolio. Use the answers to find a risk profile and recommend optimizer settings for that portfolio.

## Decision

- A risk profile belongs to one portfolio, not to the user. A user can make one portfolio more risky than another.
- Keep the questions, answer points, profile levels, and recommended settings in `backend/app/onboarding/questionnaire.json`. Do not put them in code. Each file has a `version`. Each saved profile records the version that it used.
- Each question measures one dimension:
  - `capacity`: how much loss the user can afford (time horizon, cash needs, income, savings).
  - `willingness`: how much loss the user accepts (goal, reaction to a drop, maximum loss, experience).
- Score each dimension from 0 to 100: the sum of the selected points divided by the maximum possible points. The profile score is the lower of the two scores. A user with a long horizon but low willingness is still conservative.
- Use five levels: conservative, moderately conservative, moderate, growth, aggressive. Each level has a `min_score`. The level is the highest one whose `min_score` is not more than the profile score.
- Each level maps to the current optimizer settings (Decision 005): `strategy`, `max_weight`, and `target_volatility` for `target_risk`. Do not recommend `target_return`, because a fixed return is often not possible for the selected stocks.
- Before the service recommends `target_risk`, it runs `min_variance` on the portfolio holdings. If the lowest possible volatility is more than the target, it recommends `min_variance` and tells the user why.
- The API does not send answer points to the client.
- One profile row for each portfolio. A new questionnaire replaces the old row. The row is deleted with its portfolio.
- After the user saves a new portfolio, the frontend shows a modal that asks the user to take the questionnaire. The user can skip it.
- The user must click Apply to use the recommendation. The user can change the settings after that.
- The result screen shows that the recommendation is educational, not investment advice.

## Why

- The optimizer already has strategies and limits for different risk levels. Onboarding only needs to select them.
- A data file lets the team change questions without code changes, and the version keeps old profiles understandable.
- Industry practice limits risk willingness by risk capacity.
- The feasibility check stops a recommendation that the optimizer cannot solve for the user's stocks.

## Deferred

- A history of each questionnaire attempt.
- A user-level default profile for new portfolios.
- An Assistant tool that reads the profile.
- Suggestions to add or remove assets.
