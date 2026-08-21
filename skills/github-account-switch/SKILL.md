---
name: github-account-switch
description: Switch the active GitHub account for the current repo between personal (aaronified, key id_personal) and ISB work (id_isb) by repointing the origin remote to the matching SSH host alias. Use when the user asks to switch GitHub accounts, or when a push/pull authenticates as the wrong account. SSH runs over port 443 because port 22 is firewalled.
---

# Switch GitHub account (SSH host alias)

Remotes use SSH host aliases, so the account is decided by which alias `origin`
points to — each alias offers a different key. Switching = repoint `origin`,
keeping `owner/repo` unchanged. No gh, no tokens.

Port 22 is firewalled on this network; both GitHub aliases must route SSH over 443
(`HostName ssh.github.com`, `Port 443`) in `~/.ssh/config`. If that isn't set,
connections hang — fix the config first (block at the bottom).

## Switch

Read the current path, then repoint origin, changing only the host alias:

```
git remote -v
```

Personal:

```
git remote set-url origin git@github-personal:<owner>/<repo>.git
```

ISB work:

```
git remote set-url origin git@github-isb:<owner>/<repo>.git
```

Keep `<owner>/<repo>` exactly as it already is; swap only `github-personal` <->
`github-isb`.

## Verify

```
ssh -T git@github-personal    # or git@github-isb
```

Connects over 443 and greets you as the account that alias authenticates as.

## Required ~/.ssh/config (one-time)

```
Host github-personal
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/id_personal
    IdentitiesOnly yes

Host github-isb
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/id_isb
    IdentitiesOnly yes
```
