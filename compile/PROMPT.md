Compile new raw items into the wiki by following the instructions in
compile/INSTRUCTIONS.md exactly. Only compile declared auto-eligible raw
namespaces; do not treat raw/*/* as a wildcard drop zone. When done editing, run
`python3 bin/lint.py` and fix any reported violations until it prints
"provenance OK". Do not commit, push, or create branches — leave your edits in
the working tree.
