"""The rules the workbench itself puts into every harness that provides ``permissions``.

Two lists are compiled in, like the floor, so no file can shorten them:

* ``OWNER_RUN``: the commands only the owner runs, from a terminal. A harness denies each one in
  both spellings an agent could submit, so an agent cannot install, upgrade, approve or pin.
  ``cli.py`` routes these commands, and a test fails when it routes one that is in neither this
  list nor ``AGENT_SAFE``.
* ``FLOOR_RULES``: for each hard stop of ``floor.FLOOR``, the ``ask`` rules that make the
  harness stop for the owner. They are a best-effort match on the command text an agent submits,
  not a sandbox (``trust-and-approval.md``). A stop with no entry here fails a test, so adding a
  stop to the floor cannot silently render nothing.

A rule is ``(action, tool, pattern)`` in the neutral vocabulary of ``neutral.py``.
"""

OWNER_RUN = ("install", "upgrade", "add", "attach", "acknowledge", "recover", "approve", "pin",
             "release-approvals")
# Commands an agent may run: they only read, or run a helper that checks its own pin.
AGENT_SAFE = ("verify", "preview", "launch", "check")
# `python3 -B -m workbench` is how this repository's own checks are run; the flags a rule can name
# are limited to this one. Other interpreter spellings, a path-qualified `wb`, `env` and `bash -c`
# are not matched (a Bash deny is not a security boundary).
SPELLINGS = ("wb", "python3 -m workbench", "python3 -B -m workbench", "python -m workbench",
             "python -B -m workbench")

# Not yet routed by cli.py; the drift test allows exactly these until their increment lands.
NOT_YET_ROUTED = ()

FLOOR_RULES = {
    "force-or-rewrite-history": (
        ("ask", "shell", "git push --force*"),
        ("ask", "shell", "git push -f*"),
        ("ask", "shell", "git push * --force*"),
        ("ask", "shell", "git push * -f*"),
        ("ask", "shell", "git rebase*"),
        ("ask", "shell", "git reset --hard*"),
        ("ask", "shell", "git filter-branch*"),
        ("ask", "shell", "git commit --amend*"),
    ),
    "delete-or-overwrite-files": (
        ("ask", "shell", "rm"),
        ("ask", "shell", "rm *"),
        ("ask", "shell", "git clean*"),
        ("ask", "shell", "git checkout -- *"),
        ("ask", "shell", "git checkout ."),
        ("ask", "shell", "git stash drop*"),
        ("ask", "shell", "git restore*"),
    ),
    "publish-or-deploy": (
        ("ask", "shell", "git push"),
        ("ask", "shell", "git push *"),
        ("ask", "shell", "npm publish*"),
        ("ask", "shell", "twine upload*"),
        ("ask", "shell", "cargo publish*"),
        ("ask", "shell", "docker push*"),
        ("ask", "shell", "gh release create*"),
    ),
    "touch-secrets": (
        ("ask", "read", ".env"),
        ("ask", "read", ".env.*"),
        ("ask", "read", "**/.env"),
        ("ask", "read", "**/.env.*"),
        ("ask", "read", "~/.ssh/**"),
        ("ask", "read", "~/.aws/**"),
        ("ask", "read", "~/.gnupg/**"),
    ),
    "install-dependencies": (
        ("ask", "shell", "pip install*"),
        ("ask", "shell", "pip3 install*"),
        ("ask", "shell", "python3 -m pip install*"),
        ("ask", "shell", "npm install*"),
        ("ask", "shell", "npm i"),
        ("ask", "shell", "npm i *"),
        ("ask", "shell", "npm ci*"),
        ("ask", "shell", "pnpm install*"),
        ("ask", "shell", "pnpm i"),
        ("ask", "shell", "pnpm i *"),
        ("ask", "shell", "yarn"),
        ("ask", "shell", "yarn install*"),
        ("ask", "shell", "poetry install*"),
        ("ask", "shell", "uv sync*"),
        ("ask", "shell", "bundle install*"),
        ("ask", "shell", "cargo install*"),
        ("ask", "shell", "pipx install*"),
        ("ask", "shell", "python -m pip install*"),
        ("ask", "shell", "yarn add*"),
        ("ask", "shell", "pnpm add*"),
        ("ask", "shell", "cargo add*"),
        ("ask", "shell", "go get*"),
        ("ask", "shell", "gem install*"),
        ("ask", "shell", "brew install*"),
        ("ask", "shell", "apt install*"),
        ("ask", "shell", "apt-get install*"),
        ("ask", "shell", "uv add*"),
        ("ask", "shell", "uv pip install*"),
        ("ask", "shell", "poetry add*"),
    ),
}


def owner_run_patterns():
    """The shell patterns that deny each owner-run command, bare and with arguments."""
    out = []
    for spelling in SPELLINGS:
        for command in OWNER_RUN:
            out.append("%s %s" % (spelling, command))
            out.append("%s %s *" % (spelling, command))
    return out
