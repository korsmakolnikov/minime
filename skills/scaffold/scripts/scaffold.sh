#!/usr/bin/env bash
# Render the templates of a language into the current directory, then
# initialise git with an empty "start." commit.
#
# Usage: scaffold.sh <language> KEY=VALUE [KEY=VALUE ...]
#
# Templates live in <skill dir>/<language>/templates. Every file is copied to
# the current directory with {{KEY}} placeholders (in both paths and contents)
# replaced by the given values. PROJECT_NAME is mandatory; PROJECT_IDENT
# (a valid C identifier) and PROJECT_IDENT_UPPER are derived from it.
#
# The script refuses to overwrite existing files and refuses to run if any
# placeholder is left unresolved. Scaffolded files are NOT committed.
set -euo pipefail

usage() {
    echo "usage: $0 <language> PROJECT_NAME=<name> [KEY=VALUE ...]" >&2
    exit 2
}

[ $# -ge 2 ] || usage
lang=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
shift

skill_dir=$(cd "$(dirname "$0")/.." && pwd)
tpl_dir="$skill_dir/$lang/templates"
if [ ! -d "$tpl_dir" ]; then
    echo "error: unsupported language '$lang' (no directory $tpl_dir)" >&2
    exit 1
fi

declare -A vars
for kv in "$@"; do
    case "$kv" in
        *=*) vars[${kv%%=*}]=${kv#*=} ;;
        *) echo "error: expected KEY=VALUE, got '$kv'" >&2; usage ;;
    esac
done
: "${vars[PROJECT_NAME]:?PROJECT_NAME=<name> is required}"

ident=$(printf '%s' "${vars[PROJECT_NAME]}" | tr -c 'A-Za-z0-9_' '_')
case "$ident" in [0-9]*) ident="_$ident" ;; esac
vars[PROJECT_IDENT]=$ident
vars[PROJECT_IDENT_UPPER]=$(printf '%s' "$ident" | tr '[:lower:]' '[:upper:]')

sed_args=()
for key in "${!vars[@]}"; do
    escaped=$(printf '%s' "${vars[$key]}" | sed 's/[&|\\]/\\&/g')
    sed_args+=(-e "s|{{$key}}|$escaped|g")
done
render() { sed "${sed_args[@]}"; }

mapfile -t templates < <(cd "$tpl_dir" && find . -type f | sed 's|^\./||' | sort)

# Pass 1: resolve destinations, check for conflicts and unresolved placeholders.
dests=()
for rel in "${templates[@]}"; do
    dest=$(printf '%s' "$rel" | render)
    if [ -e "$dest" ]; then
        echo "error: '$dest' already exists; refusing to overwrite" >&2
        exit 1
    fi
    if leftovers=$( { printf '%s\n' "$dest"; render < "$tpl_dir/$rel"; } | grep -o '{{[A-Z_]*}}' | sort -u) && [ -n "$leftovers" ]; then
        echo "error: unresolved placeholders in '$rel': $(printf '%s ' $leftovers)" >&2
        exit 1
    fi
    dests+=("$dest")
done

# Pass 2: write.
for i in "${!templates[@]}"; do
    mkdir -p "$(dirname "${dests[$i]}")"
    render < "$tpl_dir/${templates[$i]}" > "${dests[$i]}"
    echo "created: ${dests[$i]}"
done

# Git: only when the directory is not already inside a repository (monorepo case).
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "note: already inside a git repository ($(git rev-parse --show-toplevel)); skipping git init and the empty commit"
else
    git init
    git commit -m "start." --allow-empty
fi
