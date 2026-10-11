# Stage 1 reproduction

`python scripts/original_v1_1_blinded_annotation_v1.py --resume-existing`
verifies the closed stage namespace/code/tests plus all frozen parent/dataset hashes.

`python scripts/original_v1_1_blinded_annotation_v1.py --replay-output /tmp/new-annotation-replay`
reconstructs all chronological batches, materialized causal prefix views and annotations in a
fresh destination. Compare every generated file to QA_RECEIPT.json replay hashes.

The candidate IDs/question sets/cutoffs are frozen v3; chronological reordering is transport only.
The original unit ID and all visible prefix hashes are preserved. BATCH_MANIFEST.json fixes every
batch's candidate IDs, individual cutoffs, view file/hash and source citations hash. The annotation
index binds each candidate to a contiguous ledger record span and exact materialized view digest.
A batch maximum is never an earlier candidate's cutoff. Eight independent archive cursors expose
only completed known-prefix objects/candles. No random values/network/outcomes are needed.

To render a complete historical chart data view use the unchanged v3 materializer with the
annotation_unit_id from the batch view. Full source archives are not direct annotator input.
The source sufficiency reviewer is named accurately; no human review or exact automatic detector
is claimed. ALL answers, including UNKNOWN, retain provenance and source citation references.
Gzip mtime=0, filename empty, compact sorted JSON. Every stage is independently sealed/committed.
