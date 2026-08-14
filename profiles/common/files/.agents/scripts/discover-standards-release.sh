#!/bin/sh

LATEST_RELEASE_URL="https://github.com/lutzseverino/repository-standards/releases/latest"
RELEASE_TAG_URL="https://github.com/lutzseverino/repository-standards/releases/tag/v"

is_stable_release() {
    printf '%s\n' "$1" \
        | grep -Eq '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
}

read_adopted_release() {
    manifest=""
    for candidate in \
        .repository-standards.json \
        .repository-standards.yml \
        .repository-standards.yaml
    do
        if [ -f "$candidate" ]; then
            manifest=$candidate
            break
        fi
    done
    [ -n "$manifest" ] || return 1

    release=$(
        sed -n \
            -e 's/.*"standards-release"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
            -e "s/^[[:space:]]*standards-release[[:space:]]*:[[:space:]]*['\"]\{0,1\}\([^'\"[:space:]#]*\)['\"]\{0,1\}[[:space:]]*\(#.*\)\{0,1\}$/\1/p" \
            "$manifest" 2>/dev/null \
            | sed -n '1p'
    ) || return 1
    is_stable_release "$release" || return 1
    printf '%s\n' "$release"
}

component_is_greater() {
    left=$1
    right=$2
    if [ "${#left}" -gt "${#right}" ]; then
        return 0
    fi
    if [ "${#left}" -lt "${#right}" ] || [ "$left" = "$right" ]; then
        return 1
    fi
    LC_ALL=C awk -v left="x$left" -v right="x$right" \
        'BEGIN { exit !(left > right) }'
}

release_is_newer() {
    available=$1
    adopted=$2

    available_major=${available%%.*}
    available_rest=${available#*.}
    available_minor=${available_rest%%.*}
    available_patch=${available_rest#*.}
    adopted_major=${adopted%%.*}
    adopted_rest=${adopted#*.}
    adopted_minor=${adopted_rest%%.*}
    adopted_patch=${adopted_rest#*.}

    for pair in \
        "$available_major:$adopted_major" \
        "$available_minor:$adopted_minor" \
        "$available_patch:$adopted_patch"
    do
        left=${pair%%:*}
        right=${pair#*:}
        if component_is_greater "$left" "$right"; then
            return 0
        fi
        if component_is_greater "$right" "$left"; then
            return 1
        fi
    done
    return 1
}

if [ "$#" -eq 2 ] && [ "$1" = "--notice" ]; then
    available=$2
    is_stable_release "$available" || exit 0
    adopted=$(read_adopted_release) || exit 0
    release_is_newer "$available" "$adopted" || exit 0
    printf 'Repository standards update available: %s → %s.\n\n' \
        "$adopted" "$available"
    printf 'Start a new session in this repository and enter:\n'
    printf 'adopt-repository-standards %s\n' "$available"
    exit 0
fi

[ "$#" -eq 0 ] || exit 0

adopted=$(read_adopted_release) || exit 0
final_url=$(
    curl \
        --location \
        --fail \
        --silent \
        --max-time 3 \
        --output /dev/null \
        --write-out '%{url_effective}' \
        "$LATEST_RELEASE_URL" \
        2>/dev/null
) || exit 0

case $final_url in
    "$RELEASE_TAG_URL"*) available=${final_url#"$RELEASE_TAG_URL"} ;;
    *) exit 0 ;;
esac
is_stable_release "$available" || exit 0
release_is_newer "$available" "$adopted" || exit 0
printf '%s\n' "$available"
