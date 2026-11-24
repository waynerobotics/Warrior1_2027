# Contributing

How we pick up work, commit, and get it merged. If you haven't set up your
machine yet, start with [docs/setup.md](docs/setup.md).

## Branch structure

The general development flow is:

```text
main
  ↑
  │ approved pull request
  │
dev
  ↑
  │ pull request
  │
issue-specific branch
  │
  └── your local changes
```

**Do not develop directly on `main`.** Branches are created from `dev`, and pull requests target `dev`.

## 1. Select an issue

Before starting work, check the repository's **GitHub Issues** tab. Issues are labeled by:

* Difficulty
* Type
* Other relevant project information

Read the issue description carefully. Once you have selected an issue, assign it to yourself.

Under **Development**, select **Create branch**.

> **Branches must be created from `dev`, not `main`.**

Before creating new work, make sure your local `dev` branch is up to date:

```bash
git fetch origin
git checkout dev
git pull origin dev
```

Then create the issue-specific branch from `dev`.

GitHub can also provide the commands for creating and checking out the branch under the issue's **Development** section. Use those commands if provided. They will generally look similar to:

```bash
git fetch
git checkout <branch-name>
```

## 2. Make your changes

Work on the issue in your branch. Commit frequently rather than accumulating a large number of unrelated changes.

Before committing, check what changed and run the tests:

```bash
git status
pixi run test
```

Stage the changes you want included:

```bash
git add .
```

Commit them:

```bash
git commit -m "type-description #issue-number"
```

For example:

```bash
git commit -m "fix-correct wheel joint origin #10"
```

### Commit types

Use a short type to describe the general nature of the change:

| Type       | Purpose                                               |
| ---------- | ----------------------------------------------------- |
| `fix`      | Bug fix                                               |
| `feat`     | New functionality                                     |
| `clean`    | Cleanup                                               |
| `refactor` | Code restructuring without changing intended behavior |
| `doc`      | Documentation changes                                 |

The remainder of the commit message should briefly describe what changed.

For additional guidance on commit message conventions, see the
[Git commit message guidelines](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13).

## 3. Push your branch

Once your changes are committed:

```bash
git push
```

This pushes your commits to the remote repository so they are available to the team.

## 4. Open a pull request

Go to the GitHub repository and open a **Pull Request** targeting **`dev`**, not `main`.

The pull request should describe the broad changes made by the branch. Individual commits should already communicate the detailed changes, so the description should focus on:

* What was changed
* Why it was changed
* Any relevant implementation details
* Testing performed
* Any known limitations

## 5. Review

The pull request will be reviewed by another team member.

If changes are requested, address the review comments in your existing branch and push the additional commits:

```bash
git add .
git commit -m "fix-address-review-comments #10"
git push
```

The pull request will update automatically.

Once the changes have been reviewed and approved, the issue can be closed and the branch can be deleted.
