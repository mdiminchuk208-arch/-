# Reproducibility

Before freeze: build_original_strategy_spec_v1_1.py; unittest discover; verifier --validate; verifier --freeze. After freeze use only `python scripts/verify_original_strategy_spec_v1_1.py --resume-existing`. Verifier checks v1 resume, c2d1/archive baseline, SHA256 membership and source/resolution separation. All frozen paths immutable; subsequent QA receipts can be additive outside namespace. No financial run command.
