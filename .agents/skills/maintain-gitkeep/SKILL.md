---
name: maintain-gitkeep
description: Maintain ServerWatch directory placeholders when adding, moving, or removing version-controlled project files, or when auditing redundant .gitkeep files.
---

# Maintain directory placeholders

Git records paths to files. A directory needs a placeholder only while its intended structure would otherwise disappear from a checkout.

1. Inspect the affected directories with `git ls-files --cached --others --exclude-standard`. Count existing files, including tracked dotfiles and files in subdirectories. An ignored cache, virtual environment, local secret, or file already deleted from the working tree does not preserve the directory in a checkout.
2. Remove a redundant empty `.gitkeep` when another file in that directory or its subtree will be committed. Retain it when it is the sole file preserving the directory. For unrelated untracked files, confirm they belong in the commit before relying on them. Inspect any nonempty placeholder before changing it.
3. When moving the last real file out of a directory that the project still intends to retain, restore its empty placeholder. Review the resulting Git paths and leave staging to the caller.
