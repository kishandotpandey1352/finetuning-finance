# Milestone 3: Model Artifact Validation

## Goal

Validate the best locally fine-tuned finance adapter and prepare it for cloud deployment.

The original Milestone 3 goal was EKS GPU validation. That path was blocked because AWS GPU quota was unavailable. The project has now pivoted to deploying an already fine-tuned local adapter.

## Selected Adapter

```text
outputs/qLoRA-finance-runB-r16-lr2e4