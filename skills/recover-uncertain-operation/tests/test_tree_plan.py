"""Synthetic, offline tests. Local Git oracle writes only inside TemporaryDirectory."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "tree_plan.py"
SPEC = importlib.util.spec_from_file_location("tree_plan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
plan_tree = MODULE.plan_tree


def leaf(path, mode="100644", content=b"synthetic\n"):
    oid = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    return {"path": path, "mode": mode, "type": "blob", "sha": oid}


def replay(plan, testcase, oracle=None):
    """Model only documented immediate-entry base_tree merging, not remote success."""
    objects = {}
    for operation in plan["operations"]:
        request = operation["request"]
        testcase.assertLessEqual(len(request["tree"]), plan["max_entries"])
        testcase.assertEqual(set(request) - {"tree", "base_tree"}, set())
        if "base_tree" in request:
            testcase.assertIn(request["base_tree"], objects)
        entries = dict(objects.get(request.get("base_tree"), {}))
        for item in request["tree"]:
            testcase.assertNotIn("/", item["path"])
            if item["type"] == "tree":
                testcase.assertIn(item["sha"], objects)
            entries[item["path"]] = item
        if oracle:
            testcase.assertEqual(oracle(list(entries.values())), operation["expected_sha"])
        objects[operation["expected_sha"]] = entries
    flat = []

    def visit(oid, prefix=""):
        for entry in objects[oid].values():
            name = prefix + entry["path"]
            if entry["type"] == "tree":
                visit(entry["sha"], name + "/")
            else:
                flat.append({**entry, "path": name})

    visit(plan["root_sha"])
    return sorted(flat, key=lambda x: x["path"])


class TreePlanTests(unittest.TestCase):
    def test_empty_root_has_known_git_sha(self):
        plan = plan_tree([])
        self.assertEqual(plan["root_sha"], "4b825dc642cb6eb9a060e54bf8d69288fbee4904")
        self.assertEqual(replay(plan, self), [])

    def test_chunks_reproduce_unchanged_paths_modes_and_shas(self):
        entries = [leaf("keep.txt"), leaf("tool.sh", "100755"), leaf("link", "120000")]
        entries += [leaf(f"study/part-{i:03d}.txt", content=str(i).encode()) for i in range(85)]
        before = copy.deepcopy(entries)
        small = plan_tree(entries, max_entries=7)
        whole = plan_tree(entries, max_entries=1000)
        self.assertEqual(small["root_sha"], whole["root_sha"])
        self.assertEqual(replay(small, self), sorted(entries, key=lambda x: x["path"]))
        self.assertEqual(entries, before)
        self.assertTrue(any("base_tree" in x["request"] for x in small["operations"]))

    def test_plan_is_deterministic_under_input_permutation(self):
        entries = [leaf(f"d{i % 3}/p-{i:03d}") for i in range(35)]
        expected = plan_tree(entries, max_entries=4)
        random.Random(15).shuffle(entries)
        self.assertEqual(plan_tree(entries, max_entries=4), expected)

    def test_rejects_duplicate_and_file_directory_collisions_in_both_orders(self):
        for entries in ([leaf("a"), leaf("a")], [leaf("a"), leaf("a/b")],
                        [leaf("a/b"), leaf("a")]):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                plan_tree(entries)

    def test_rejects_paths_outside_explicit_ascii_subset_without_normalizing(self):
        for path in ("", "/a", "a/", "a//b", ".", "..", "a/../b", "a/./b",
                     ".git/config", ".GIT/config", "a\\b", "a b", "caf\u00e9", "a\0b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                plan_tree([leaf(path)])

    def test_rejects_non_blob_modes_null_shas_and_content(self):
        bad = [dict(leaf("a"), mode="160000", type="commit"),
               dict(leaf("a"), mode="040000", type="tree"),
               dict(leaf("a"), mode="100664"), dict(leaf("a"), sha=None),
               dict(leaf("a"), sha="a" * 64), dict(leaf("a"), sha="Z" * 40),
               dict(leaf("a"), content="do not rewrite"), {"path": "a"}]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):
                plan_tree([item])

    def test_rejects_invalid_chunk_caps(self):
        for size in (0, -1, True, 2.5, "40"):
            with self.subTest(size=size), self.assertRaises(ValueError):
                plan_tree([], max_entries=size)

    def test_accepts_64_path_components_but_rejects_65(self):
        path = "/".join(["d"] * 63 + ["f"])
        self.assertEqual(replay(plan_tree([leaf(path)]), self), [leaf(path)])
        with self.assertRaises(ValueError):
            plan_tree([leaf("d/" + path)])

    def test_deduplicates_identical_subtree_objects(self):
        entries = [leaf("a/file"), leaf("b/file")]
        plan = plan_tree(entries)
        self.assertEqual(len(plan["operations"]), 2)
        self.assertEqual(replay(plan, self), entries)

    def test_mode_and_path_changes_change_identity(self):
        original = plan_tree([leaf("a")])["root_sha"]
        self.assertNotEqual(original, plan_tree([leaf("b")])["root_sha"])
        self.assertNotEqual(original, plan_tree([leaf("a", "100755")])["root_sha"])

    @unittest.skipUnless(shutil.which("git"), "optional independent local Git oracle")
    def test_all_intermediates_match_git_mktree_including_directory_sort(self):
        entries = [leaf("foo.c"), leaf("foo/file"), leaf("foo0"), leaf("foo.bar"),
                   leaf("exec", "100755"), leaf("link", "120000")]
        entries += [leaf(f"many/p-{i:03d}") for i in range(41)]
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "--bare", "--object-format=sha1", directory],
                           check=True, capture_output=True)

            def oracle(items):
                data = "".join(f'{e["mode"]} {e["type"]} {e["sha"]}\t{e["path"]}\n'
                               for e in reversed(items)).encode("ascii")
                return subprocess.run(["git", "-C", directory, "mktree", "--missing"],
                                      input=data, check=True, capture_output=True).stdout.decode().strip()

            for cap in (1, 3, 40, 1000):
                self.assertEqual(replay(plan_tree(entries, cap), self, oracle),
                                 sorted(entries, key=lambda x: x["path"]))


if __name__ == "__main__":
    unittest.main()
