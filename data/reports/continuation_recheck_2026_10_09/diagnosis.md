# Initial validation-helper diagnostic

The frozen pipeline itself returned exit code 0 and a complete 45-study inventory.
The initial helper compared the complete before/after path sets for equality.
An independent source-audit script and its new report were added while it ran;
new files incorrectly triggered `original_files_unchanged=false`.

This initial receipt is retained as a failed helper validation, not final evidence
of readiness. The helper now checks that every original path retains its original
hash and separately lists additions. The repeated verified validation has no
changed original paths. Neither the baseline guard nor expected fingerprints
were relaxed, and no old artifacts were replaced.
