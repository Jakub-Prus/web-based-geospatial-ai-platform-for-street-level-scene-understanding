# 16. AI-Assisted Development

Status: Proposed v1

## Purpose

This document explains how AI-assisted engineering supports the delivery of this project, matching the role's explicit AI-first expectation.

## Intended Usage

- Use AI coding assistants to scaffold service boilerplate and frontend component shells
- Use LLM support to draft API payloads, validation rules, and test cases
- Use AI-assisted debugging to diagnose data-ingestion failures, overlay misalignment, and annotation edge cases
- Use AI-generated test suggestions to improve backend and frontend regression coverage

## Guardrails

- AI assistance accelerates implementation but does not replace architectural decisions
- All generated code must be reviewed and adjusted to match the dataset and geometry contracts
- High-risk logic such as coordinate handling, depth scaling, and annotation persistence must be manually verified

## Evidence To Show

- README note describing where AI accelerated delivery
- Commit history or notes showing iterative use of AI for scaffolding and refinement
- Automated tests or validation scripts improved with AI assistance

## Interview Value

This helps demonstrate that the project was built with an AI-first engineering workflow while still preserving technical judgment and ownership.
