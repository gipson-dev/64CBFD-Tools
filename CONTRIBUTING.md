# Contributing

## Ownership

Change tools, candidate drivers, fixtures, and test oracles in this repository.
Change game sources, compiler profiles, retail manifests, word guards, and
function working notes in [64CBFD](https://github.com/gipson-dev/64CBFD).
Preserve upstream submodule boundaries and identify dependency-pin updates
explicitly. Do not include game assets, ROMs, secrets, or generated receipts.

## Validate

Run the ROM-free checks in [README.md](README.md). Matching tests additionally
run from a prepared decomp checkout, with this repository at its `tools/`
path. Use focused tests appropriate to the change; shared layout, linker, or
padder changes need broader regression coverage and a before/after game audit.
State exactly which commands passed, skipped, or need private/local inputs.

## Update The Consumer

The standalone `64CBFD Tools` folder and `64CBFD/tools` are separate Git
checkouts of the same repository. Editing one does not silently edit the other.
Matching work can be developed directly in the mounted `64CBFD/tools` checkout;
commit tool changes there before recording the parent pin. Alternatively,
commit in the standalone folder, then fetch and check out that commit in the
mounted copy before testing. A local commit can be fetched from the sibling
path before publication:

```sh
# Run from 64CBFD. Fetch an exact committed revision from the sibling checkout.
git -C tools fetch "../../64CBFD Tools" master
git -C tools checkout --detach FETCH_HEAD
git -C tools submodule update --init --recursive
make tools-check
# Run the relevant matching/regression checks here as well.
```

Publish the tools commit before publishing the consumer pin, so recursive
clones can resolve it. From the decomp root:

```sh
git -C tools push origin HEAD:master
git add tools
git commit -m "Update pinned decomp tools"
git push origin master
```

Never use `git submodule update --remote` as a build/setup command; builds
must use the recorded revision. Do not force-checkout a dirty tools copy.

## Reports And Pull Requests

Tool defects belong here; function-recovery and game-source defects belong in
the decomp repository. Include the tools SHA and decomp SHA, platform/toolchain,
reproduction command, measured outcome, and qualification limits. Attach
small synthetic fixtures rather than copyrighted ROM content.
