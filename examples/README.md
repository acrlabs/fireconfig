# 🔥Config Examples

## Workflows

The workflows directory contains a set of GitHub actions that you can use to have 🔥Config automatically compute the
mermaid DAG and diff of changes to your Kubernetes objects, and then leave a comment on the PR with the DAG and diff.
You _should_ just be able to copy these into your `.github/workflows` directory.  You'll need to set up a personal
access token (PAT) with read access to your actions and read and write access to pull requests.  This PAT then needs to
be injected into your actions as a GitHub secret.

- [Managing your Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Using secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)
