**NEVER** edit this file. 

## Note

**ALWAYS** include the commit type, context, description for each file edited, and explanation for why a change was made. 

**ALWAYS** use one of the following commit types 
feat|fix|chore|test|docs|refractor|style|perf|build|ci 

**AlWAYS** check that the source code has proper testing included 

## Commit Template 

<commit-type>: <short summary of the change>

**Commit type:** <feat|fix|chore|test|docs|refractor|style|perf|build|ci>

**Context:** <Describe the problem or requirement behind the change.>

**Files edited:**

- **`<path/to/file>`**
  - **Description:** <Describe what changed in this file.>
  - **Why:** <Explain why this change was necessary.>

- **`<path/to/another/file>`**
  - **Description:** <Describe what changed in this file.>
  - **Why:** <Explain why this change was necessary.>

**Testing:**

- **Coverage reviewed:** <Confirm appropriate tests cover the source changes; identify any gaps.>
- **Tests added or updated:** <List the scenarios covered, or explain why no test changes were needed.>
- **Tests run:** <Commands or test suites executed.>
- **Results:** <Pass/fail results; explicitly state if tests were not run and why.>


## Commit Example 
"
fix: prevent login failures caused by whitespace in email address

Context: Users cannot sign in when a pasted email address contains leading or trailing spaces.

Files edited:

src/auth/login.ts

Description: Trim the email address before account lookup.

Why: Accidental whitespace should not cause valid credentials to fail.

tests/auth/login.test.ts

Description: Add tests for leading spaces, trailing spaces, surrounding spaces, and unchanged valid input.

Why: Verify the fix and protect existing login behavior from regressions.

Testing: Reviewed coverage for the changed login behavior. All four scenarios are covered, and the authentication test suite passes.
"