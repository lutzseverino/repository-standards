#!/bin/sh

LATEST_RELEASE_URL="https://github.com/lutzseverino/repository-standards/releases/latest"
RELEASE_TAG_URL="https://github.com/lutzseverino/repository-standards/releases/tag/v"

is_stable_release() {
    printf '%s\n' "$1" \
        | grep -Eq '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
}

read_json_release() {
    awk '
        BEGIN { depth = 0; state = "root" }
        {
            for (cursor = 1; cursor <= length($0); cursor++) {
                character = substr($0, cursor, 1)
                if (in_string) {
                    if (escaped) {
                        token = token character
                        escaped = 0
                    } else if (character == "\\") {
                        escaped = 1
                    } else if (character == "\"") {
                        in_string = 0
                        if (role == "key") {
                            key = token
                            state = "colon"
                        } else if (role == "value") {
                            if (key == "standards-release") {
                                release = token
                                releases++
                            }
                            state = "after-value"
                        }
                        role = ""
                    } else {
                        token = token character
                    }
                    continue
                }
                if (character == "{") {
                    depth++
                    if (depth == 1) state = "key"
                } else if (character == "}") {
                    depth--
                } else if (character == "," && depth == 1) {
                    state = "key"
                } else if (character == ":" && depth == 1 && state == "colon") {
                    state = "value"
                } else if (character == "\"") {
                    in_string = 1
                    token = ""
                    if (depth == 1 && state == "key") role = "key"
                    else if (depth == 1 && state == "value") role = "value"
                    else role = "other"
                }
            }
        }
        END { if (releases == 1) print release }
    ' "$1"
}

read_yaml_release() {
    awk '
        {
            lines[NR] = $0
            if ($0 ~ /^[[:space:]]*$/ || $0 ~ /^[[:space:]]*(#|---|\.\.\.)/) next
            match($0, /^ */)
            indentation = RLENGTH
            content = substr($0, indentation + 1)
            separator = index(content, ":")
            if (!separator) next
            key = substr(content, 1, separator - 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
            if (!length(key)) next
            if (!root_found || indentation < root_indentation) {
                root_indentation = indentation
                root_found = 1
            }
        }
        END {
            for (line_number = 1; line_number <= NR; line_number++) {
                line = lines[line_number]
                match(line, /^ */)
                indentation = RLENGTH
                if (!root_found || indentation != root_indentation) continue
                content = substr(line, indentation + 1)
                separator = index(content, ":")
                if (!separator) continue
                key = substr(content, 1, separator - 1)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
            if (key != "standards-release" && key != "\047standards-release\047" \
                    && key != "\"standards-release\"") continue
                value = substr(content, separator + 1)
                sub(/^[[:space:]]+/, "", value)
                sub(/[[:space:]]+#.*$/, "", value)
                sub(/[[:space:]]+$/, "", value)
                if ((substr(value, 1, 1) == "\"" \
                    && substr(value, length(value), 1) == "\"") \
                    || (substr(value, 1, 1) == "\047" \
                        && substr(value, length(value), 1) == "\047")) {
                    value = substr(value, 2, length(value) - 2)
                }
                release = value
                releases++
            }
            if (releases == 1) print release
        }
    ' "$1"
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

    case $manifest in
        *.json) release=$(read_json_release "$manifest") || return 1 ;;
        *) release=$(read_yaml_release "$manifest") || return 1 ;;
    esac
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
    printf 'adopt-standards %s\n' "$available"
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
