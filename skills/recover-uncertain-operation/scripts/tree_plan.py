"""Pure SHA-1 tree planner; never calls a service or changes files, commits or refs.

Input is the COMPLETE final flat leaf manifest, not a patch. Each record has
exactly path/mode/type/sha. Blob modes: 100644, 100755, 120000. Paths use 1..64
slash-separated ASCII [A-Za-z0-9._-]+ components, excluding '.', '..', '.git'
(case-insensitive). No rewriting, existence checks, empty directories, gitlinks,
explicit tree entries, deletions, SHA-256 repositories or arbitrary byte paths.
"""
import hashlib
import re


def _order(entry):
    # Git compares a directory basename as though it ended in '/'.
    return entry["path"].encode("ascii") + (b"/" if entry["type"] == "tree" else b"")


def _tree_sha(entries):
    data = b"".join(
        f'{int(e["mode"], 8):o} {e["path"]}'.encode("ascii") + b"\0" + bytes.fromhex(e["sha"])
        for e in sorted(entries, key=_order)
    )
    return hashlib.sha1(b"tree " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def plan_tree(entries, max_entries=40):
    """Return expected root and bottom-up requests; no authorization to execute them.

    Requests contain only immediate names and existing object IDs. Later chunks
    use the preceding partial tree as base_tree. The cap limits request entries,
    not final directory width, response size, request bytes, time or API limits.
    """
    if type(max_entries) is not int or max_entries < 1:
        raise ValueError("max_entries must be a positive integer")
    root = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"path", "mode", "type", "sha"}:
            raise ValueError("each leaf needs exactly path, mode, type, sha")
        if item["type"] != "blob" or item["mode"] not in ("100644", "100755", "120000"):
            raise ValueError("unsupported leaf type or mode")
        sha = item["sha"]
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("sha must be a lowercase SHA-1 object ID")
        path = item["path"]
        parts = path.split("/") if isinstance(path, str) else []
        if not 1 <= len(parts) <= 64 or any(
            not re.fullmatch(r"[A-Za-z0-9._-]+", p) or p.lower() in (".", "..", ".git")
            for p in parts
        ):
            raise ValueError("path is outside the supported canonical ASCII subset")
        node = root
        for part in parts[:-1]:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                raise ValueError("file/directory collision")
            node = child
        if parts[-1] in node:
            raise ValueError("duplicate path or file/directory collision")
        node[parts[-1]] = (item["mode"], sha)

    operations = []
    emitted = set()

    def visit(node):
        children = []
        for name, child in sorted(node.items()):
            if isinstance(child, dict):
                entry = {"path": name, "mode": "040000", "type": "tree", "sha": visit(child)}
            else:
                entry = {"path": name, "mode": child[0], "type": "blob", "sha": child[1]}
            children.append(entry)
        children.sort(key=_order)
        cumulative = []
        previous = None
        for offset in range(0, max(1, len(children)), max_entries):
            chunk = children[offset:offset + max_entries]
            cumulative.extend(chunk)
            expected = _tree_sha(cumulative)
            request = {"tree": chunk}
            if previous is not None:
                request["base_tree"] = previous
            if expected not in emitted:
                operations.append({"expected_sha": expected, "request": request})
                emitted.add(expected)
            previous = expected
        return previous

    final = visit(root)
    return {"root_sha": final, "max_entries": max_entries, "operations": operations}
