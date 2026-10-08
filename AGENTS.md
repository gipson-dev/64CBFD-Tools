# Decomp Tools Agent Instructions

Use the consumer's [Codex and Claude workflow](https://github.com/gipson-dev/64CBFD/blob/master/DOCS/AGENT_WORKFLOW.md)
and current target working note. In the shared workspace, the local policy is
`64CBFD/DOCS/AGENT_WORKFLOW.md`; the GitHub link is effective after publication.

Codex is the single writer. Claude is an optional packet-only reviewer;
routine tasks use zero calls. Preserve unrelated edits, upstream pins and
private inputs. Do not commit, publish or change the consumer pin unless asked.

Reuse existing parsers, compiler fixtures and MIPS/native32 oracles. Most
function tests need this repository mounted at `64CBFD/tools`; standalone
checks are listed in [README.md](README.md). Record fresh checks separately
from prior unchanged receipts. Validate affected tools in both local copies,
without overwriting conflicting work. Keep transient packets/logs in the
consumer's ignored target build directory, not in this tools repository.
