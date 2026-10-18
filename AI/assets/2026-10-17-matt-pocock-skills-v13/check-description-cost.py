"""Static description audit, not a tokenizer or a runtime benchmark."""
import json
import re
import subprocess
import sys

import yaml

repo = sys.argv[1]


def show(ref, path):
    return subprocess.check_output(["git", "-C", repo, "show", f"{ref}:{path}"], text=True)


def length(value):
    return len(value.encode("utf-16-le")) // 2


for ref in ["221ffca^", "221ffca", "6a62d72^", "6a62d72", "47bde84", "49dd158"]:
    manifest = json.loads(show(ref, ".claude-plugin/plugin.json"))
    rows = []
    for directory in manifest["skills"]:
        content = show(ref, directory.removeprefix("./") + "/SKILL.md")
        metadata = yaml.safe_load(content.split("---", 2)[1])
        description = re.sub(r"\s+", " ", metadata.get("description", "")).strip()
        rows.append((metadata["name"], length(description), not metadata.get("disable-model-invocation", False)))
    visible = [row for row in rows if row[2]]
    print(json.dumps({"ref": ref, "skills": len(rows), "visible": len(visible), "all_chars": sum(r[1] for r in rows), "visible_chars": sum(r[1] for r in visible), "family": [r for r in visible if r[0] in {"grill-me", "grill-with-docs", "grilling", "domain-modeling"}]}, ensure_ascii=False))

# Independently explain the handoff's HEAD-only discrepancy and check policy pairs.
manifest = json.loads(show("49dd158", ".claude-plugin/plugin.json"))
raw_rows = []
differences = []
explicit_count = 0
for directory in manifest["skills"]:
    base = directory.removeprefix("./")
    content = show("49dd158", base + "/SKILL.md")
    metadata = yaml.safe_load(content.split("---", 2)[1])
    raw = next(line.split(":", 1)[1].strip() for line in content.splitlines() if line.startswith("description:"))
    hidden = metadata.get("disable-model-invocation", False)
    policy = yaml.safe_load(show("49dd158", base + "/agents/openai.yaml"))
    explicit = policy.get("policy", {}).get("allow_implicit_invocation", True) is False
    assert hidden == explicit, metadata["name"]
    explicit_count += explicit
    raw_rows.append((length(raw), not hidden))
    delta = length(raw) - length(metadata["description"])
    if delta:
        differences.append({"name": metadata["name"], "extra_yaml_chars": delta, "visible": not hidden})
print(json.dumps({"raw_yaml_all": sum(r[0] for r in raw_rows), "raw_yaml_visible": sum(r[0] for r in raw_rows if r[1]), "differences": differences, "matching_explicit_only_policies": explicit_count}))
