# Recover an exact content-addressed Git tree

Use this example when an authorized Git tree creation times out and the intended
tree is independently computable. It does not authorize writes, broaden an
approved release, or replace the general uncertain-operation ledger.

## Identity is not an effect receipt

Git names an object from its serialized contents and object header. For a tree,
those contents encode child names, modes and object IDs in Git's canonical order.
There are no author or timestamp fields. Identical final tree contents therefore
produce the same object ID, including when reached through different construction
plans. This is an inference from [Git's object model](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects),
not a general HTTP retry guarantee.

- A repeated message may create another message. A tree request with identical
  immutable inputs denotes the same tree, not another logical release.
- A commit is also content-addressed, but its full contents include author,
  committer, dates, parents and message. [GitHub defaults the author date to the
  current date](https://docs.github.com/en/rest/git/commits#create-a-commit).
  Repeating a request with omitted dates need not create the same commit. Do not
  transfer the tree argument to a default-timestamp commit retry.
- A branch is mutable state. Tree creation neither publishes a commit nor moves
  the branch. Treat each publication outcome as a separate reconciliation task.

## Freeze, reconcile, reconstruct, verify

1. Preserve a secret-free local ledger: exact repository and target, authorization
   scope, old head/tree, frozen intended path/mode/type/object-ID manifest,
   independently expected final root, and each attempt's inputs, timeout or
   response, and subsequent observations. Keep unknown attempts unknown even if
   another route establishes the desired final state. Do not publish raw receipts.
2. Read the expected object by its hash in the correct repository. Validate its
   identity and complete contents if found. A missing, failed or stale read does
   not certify non-execution. In particular, [GitHub documents several reasons
   for a 422](https://docs.github.com/en/rest/git/trees#get-a-tree); it is not an
   absence certificate. If a read is truncated, fetch immediate subtrees until
   the manifest is complete. Honor access denials and service backoff.
3. Before changing construction strategy, independently reproduce the old root
   from a complete old manifest. Combine the approved changes with every
   unaffected old entry and compute the expected new root. Stop on a mismatch,
   missing entries, unsupported modes, or an uncertain baseline. Counts alone do
   not verify preservation.
4. If object creation remains authorized, construct final directory trees from
   the leaves upward. Use existing blob IDs without rewriting bytes. For a wide
   directory, add disjoint immediate-name chunks, using the previous partial tree
   as the next request's base_tree. [GitHub's documented merge semantics](https://docs.github.com/en/rest/git/trees#create-a-tree)
   preserve base entries and overwrite matching paths. Use no overlapping parent
   tree and nested-path entries. Omit base_tree only when the supplied entries
   intentionally define the whole starting tree, not as an accidental deletion.
5. Record the expected hash for every intermediate request. Check each returned
   hash or reconcile an uncertain response by that expected hash before relying
   on it as a dependency. A late original creation still denotes the same object.
   Partial staging trees need not be referenced by any commit. Unreferenced does
   not mean private, and is not a retention guarantee.
6. Require the final root to match the independent expected hash. Verify every
   approved path, mode and object ID and all required old entries from complete
   readback. A smaller batch succeeding does not prove the timeout's cause.

A timeout is uncertainty, not a denial. An explicit denial stops the denied
action: never change batching, credentials, interfaces or paths to circumvent it.
The content-addressed argument concerns duplicate object identity, not permission,
rate limits, resource cost, confidentiality, or service availability.

## Publish only the verified final state

After verification, create the intended commit separately within authorization.
If that action times out, reconcile its actual full commit identity and state
instead of blindly creating another default-timestamp commit. Then publish with
a non-force update and an expected-old-head guard where the interface supports
one; if the head changed, stop and reconcile rather than silently rebasing or
overwriting. Inspect the final branch head and commit tree after the update.

Do not invent a compare-and-swap parameter: [GitHub REST Update a reference](https://docs.github.com/en/rest/git/refs#update-a-reference)
documents sha and force, not an expected-old-head argument. force=false enforces
fast-forward, not equality to a particular observed head. A separate read is not
an atomic guard. [Git update-ref with old-oid](https://git-scm.com/docs/git-update-ref)
illustrates an explicit old-value check; use only the verified guarantees of the
actual publication interface. If a required guard is unavailable, stop that step.

## Observed recovery, not a timeout benchmark

In one recovery observation, two identical requests covering 388 reviewed,
SHA-only blob paths each returned ReadTimeout after about 18 seconds. All blobs
already existed. The independently expected root was
c8a29f16228de3770b5623076ec692cf65f0493b; an initial lookup returned 422.
After reproducing the old root, a bottom-up plan of 21 partial/directory trees,
at most 40 request entries each, assembled that same final root. Verification
covered all 388 intended path/mode/hashes and 272 old non-tree entries. One commit
and a non-force, expected-head-checked publication followed.

The [public commit](https://github.com/EastonSell/representation-atlas/commit/cba638dc3e107612c8e50f893f37540697219daf)
and [resulting study](https://github.com/EastonSell/representation-atlas/tree/cba638dc3e107612c8e50f893f37540697219daf/studies/copy-activation-interchange)
anchor the final state; the [public commit object](https://api.github.com/repos/EastonSell/representation-atlas/git/commits/cba638dc3e107612c8e50f893f37540697219daf)
records the expected root. The timeout, timing and recovery-plan figures above
are an observation summary, not facts reconstructible from that final commit
alone. No raw operational receipts are included. This case demonstrates one
successful route. It does not establish that entry count caused either timeout,
that 40 is an API limit, or that the same strategy will always succeed.

## Tiny offline planner

[tree_plan.py](../scripts/tree_plan.py) is a pure Python 3.10+ example. Call
plan_tree(complete_final_manifest, max_entries=40). It returns root_sha and an
ordered operations list, each containing expected_sha and a GitHub-shaped
request with tree and optional base_tree. It executes nothing. Validate the old
root and the independently expected final root outside this planner before using
any plan. Do not use the planner's own output as its only correctness oracle.

Supported inputs are deliberately narrow:
- Complete flat final leaf manifest, not a change list or incomplete recursive
  response. Each record has exactly path, mode, type and sha; type must be blob.
- SHA-1 repository, 40 lowercase hexadecimal object IDs, and already-existing
  blobs. Existence and blob bytes are caller checks, not claims made by this code.
- Modes 100644, 100755 and 120000. Paths have 1 to 64 slash-separated ASCII
  [A-Za-z0-9._-]+ components; '.', '..' and case-insensitive '.git' are rejected.
  The code never normalizes or renames a path.
- No gitlinks, explicit input tree entries, empty directory preservation, null-SHA
  deletions, SHA-256 object IDs, Unicode or arbitrary byte paths. If the baseline
  needs these, use a separately verified implementation; never drop those entries
  to fit this example. The cap bounds request entry count, not bytes or runtime.

Run from the repository root:

```sh
python -m unittest discover -s skills/recover-uncertain-operation/tests -v
```

The synthetic tests check exact leaf preservation, input-order determinism,
chunk-size invariance, Git's directory sorting and rejection boundaries. An
optional independent [git mktree](https://git-scm.com/docs/git-mktree) oracle
checks every intermediate in a temporary local repository. There are no network
calls or live publication tests. These tests establish neither hosted timeout
reliability nor that a model will follow this guide. Primary sources checked
October 22, 2026; Git's [tree comparator source](https://github.com/git/git/blob/master/tree.c)
also specifies the directory-name sorting rule used here.
