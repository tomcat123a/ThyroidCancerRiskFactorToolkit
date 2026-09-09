# GitHub Sync Guide

After you create an empty GitHub repository, run these commands inside `github_repo/`:

```bash
git init
git add .
git commit -m "Initial open-source release for THCA risk factor toolkit"
git branch -M main
git remote add origin <your-github-repository-url>
git push -u origin main
```

If the remote repository already exists and has no files, the same sequence works directly.

If the remote repository already contains a README or other bootstrap files, pull first:

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```
