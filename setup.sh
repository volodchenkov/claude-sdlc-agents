#!/usr/bin/env bash
# setup.sh — install the SDLC agent pack.
#
# Interactive: pick which CLIs to install (gh, glab, kubectl, helm, jq) and
# which integration points to wire up (agent symlinks into ~/.claude/agents/,
# slash-command symlinks into ~/.claude/commands/, plane-tower MCP check).
#
# Pure check + install — does NOT modify ~/.claude/settings.json. The
# permissions allowlist for read-only patterns is documented in
# `docs/settings-snippet.md`; merge it into your settings.json yourself.
#
# Re-run safe: every step skips work that's already done.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"

# ---------- pretty printing ----------
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }
hr()     { printf '%50s\n' '' | tr ' ' '-'; }

# ---------- OS detection ----------
OS=""
case "$(uname -s)" in
  Linux*)   OS="linux" ;;
  Darwin*)  OS="macos" ;;
  *)        red "unsupported OS: $(uname -s)"; exit 1 ;;
esac

# ---------- ask helper (Y/n with default Y) ----------
ask_yn() {
  # ask_yn "Prompt" [default=Y]
  local prompt="$1" default="${2:-Y}" reply
  local hint="[Y/n]"
  [[ "$default" =~ ^[Nn]$ ]] && hint="[y/N]"
  read -r -p "$prompt $hint " reply </dev/tty || reply=""
  reply="${reply:-$default}"
  [[ "$reply" =~ ^[Yy]$ ]]
}

# ---------- CLI installers ----------
have() { command -v "$1" >/dev/null 2>&1; }

install_gh() {
  if [[ "$OS" == "macos" ]]; then
    have brew || { red "brew not found — install Homebrew first (https://brew.sh)"; return 1; }
    brew install gh
  else
    # Debian / Ubuntu / Mint — official keyring instructions
    if have apt; then
      sudo install -dm 755 /etc/apt/keyrings
      curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
      sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
      sudo apt update && sudo apt install -y gh
    else
      red "no apt — install gh manually: https://github.com/cli/cli#installation"
      return 1
    fi
  fi
}

install_glab() {
  if [[ "$OS" == "macos" ]]; then
    have brew && brew install glab && return 0
  fi
  if have apt; then
    # Latest .deb from gitlab-org/cli releases
    local arch tmp
    arch=$(dpkg --print-architecture)
    tmp=$(mktemp -d)
    curl -fsSL "https://gitlab.com/gitlab-org/cli/-/releases/permalink/latest/downloads/glab_${arch}.deb" -o "$tmp/glab.deb"
    sudo dpkg -i "$tmp/glab.deb"
    rm -rf "$tmp"
  else
    red "install glab manually: https://gitlab.com/gitlab-org/cli#installation"
    return 1
  fi
}

install_kubectl() {
  if [[ "$OS" == "macos" ]]; then
    have brew && brew install kubectl && return 0
  fi
  if have apt; then
    sudo install -dm 755 /etc/apt/keyrings
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key \
      | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' \
      | sudo tee /etc/apt/sources.list.d/kubernetes.list >/dev/null
    sudo apt update && sudo apt install -y kubectl
  else
    red "install kubectl manually: https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/"
    return 1
  fi
}

install_helm() {
  if [[ "$OS" == "macos" ]]; then
    have brew && brew install helm && return 0
  fi
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
}

install_jq() {
  if [[ "$OS" == "macos" ]]; then
    have brew && brew install jq && return 0
  fi
  have apt && sudo apt install -y jq
}

install_helm_diff() {
  have helm || { red "helm not installed — skip helm-diff"; return 1; }
  helm plugin list 2>/dev/null | grep -q '^diff' && { yellow "helm-diff already installed"; return 0; }
  helm plugin install https://github.com/databus23/helm-diff
}

# ---------- step 1: pick CLIs ----------

declare -A TOOLS=(
  [gh]="GitHub CLI"
  [glab]="GitLab CLI"
  [kubectl]="Kubernetes CLI"
  [helm]="Helm package manager"
  [jq]="JSON CLI processor"
  [helm-diff]="helm-diff plugin (recommended for safe upgrades)"
)
ORDER=(gh glab kubectl helm jq helm-diff)

declare -A INSTALL=()

green "=== Step 1: choose CLIs to install ==="
for tool in "${ORDER[@]}"; do
  desc="${TOOLS[$tool]}"
  if have "$tool" 2>/dev/null \
     || ([[ "$tool" == helm-diff ]] && helm plugin list 2>/dev/null | grep -q '^diff'); then
    green "  ✓ $tool already installed ($desc) — skipping"
    INSTALL[$tool]=0
    continue
  fi
  if ask_yn "  $tool not found ($desc). install?" Y; then
    INSTALL[$tool]=1
  else
    INSTALL[$tool]=0
  fi
done

hr
for tool in "${ORDER[@]}"; do
  [[ "${INSTALL[$tool]:-0}" == 1 ]] || continue
  green "Installing $tool..."
  case "$tool" in
    gh)         install_gh ;;
    glab)       install_glab ;;
    kubectl)    install_kubectl ;;
    helm)       install_helm ;;
    jq)         install_jq ;;
    helm-diff)  install_helm_diff ;;
  esac || red "  install of $tool failed — continue"
done

# ---------- step 2: auth status ----------

hr
green "=== Step 2: auth status (informational) ==="
if have gh; then
  if gh auth status >/dev/null 2>&1; then
    green "  ✓ gh authenticated"
  else
    yellow "  ! gh not authenticated — run: gh auth login"
  fi
fi
if have glab; then
  if glab auth status >/dev/null 2>&1; then
    green "  ✓ glab authenticated"
  else
    yellow "  ! glab not authenticated — run: glab auth login"
  fi
fi
if have kubectl; then
  if kubectl config current-context >/dev/null 2>&1; then
    green "  ✓ kubectl context: $(kubectl config current-context)"
  else
    yellow "  ! kubectl has no current context — populate ~/.kube/config"
  fi
fi
if have helm; then
  green "  ✓ helm $(helm version --short 2>/dev/null)"
fi

# ---------- step 3: install agent prompts as symlinks ----------

hr
green "=== Step 3: install agent prompts ==="

if ask_yn "  symlink agent prompts into $CLAUDE_HOME/agents/?" Y; then
  mkdir -p "$CLAUDE_HOME/agents"
  for f in "$REPO/agents/"*.md; do
    name="$(basename "$f")"
    target="$CLAUDE_HOME/agents/$name"
    if [[ -L "$target" || -e "$target" ]]; then
      yellow "  ~ $name already exists — skipping (remove manually if you want a fresh symlink)"
      continue
    fi
    ln -s "$f" "$target"
    green "  ✓ linked $name"
  done
fi

# ---------- step 4: install slash commands ----------

hr
green "=== Step 4: install slash commands ==="
if [[ -d "$REPO/commands" ]] && ask_yn "  symlink slash commands into $CLAUDE_HOME/commands/?" Y; then
  mkdir -p "$CLAUDE_HOME/commands"
  for f in "$REPO/commands/"*.md; do
    [[ -e "$f" ]] || continue
    name="$(basename "$f")"
    target="$CLAUDE_HOME/commands/$name"
    if [[ -L "$target" || -e "$target" ]]; then
      yellow "  ~ /$name already exists — skipping"
      continue
    fi
    ln -s "$f" "$target"
    green "  ✓ linked /$name"
  done
fi

# ---------- step 5: plane-tower MCP check ----------

hr
green "=== Step 5: plane-tower MCP ==="
if [[ -f "$HOME/.claude.json" ]] && grep -q '"plane-tower"' "$HOME/.claude.json" 2>/dev/null; then
  green "  ✓ plane-tower MCP is registered in ~/.claude.json"
else
  yellow "  ! plane-tower MCP is not registered."
  yellow "    Install plane-conductor and register the MCP per its README:"
  yellow "    https://github.com/volodchenkov/plane-conductor"
fi

# ---------- step 6: settings.json allowlist ----------

hr
green "=== Step 6: settings.json read-only allowlist ==="
SETTINGS="$CLAUDE_HOME/settings.json"
SNIPPET="$REPO/docs/settings-allowlist.json"
if [[ ! -f "$SNIPPET" ]]; then
  red "  ! $SNIPPET missing — skipping"
elif ! have jq; then
  yellow "  jq not installed — cannot merge automatically. See docs/settings-snippet.md"
elif ask_yn "  merge read-only Bash allowlist into $SETTINGS?" Y; then
  mkdir -p "$CLAUDE_HOME"
  if [[ ! -s "$SETTINGS" ]]; then
    echo '{}' > "$SETTINGS"
  fi
  # Backup before any rewrite.
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d-%H%M%S)"
  # Merge: union the existing permissions.allow with our recommended set, dedup.
  tmp=$(mktemp)
  jq --slurpfile add "$SNIPPET" '
    .permissions //= {}
    | .permissions.allow //= []
    | .permissions.allow = ((.permissions.allow + $add[0].allow) | unique)
  ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  green "  ✓ allowlist merged. Backup at $SETTINGS.bak.*"
fi

hr
green "Done."
