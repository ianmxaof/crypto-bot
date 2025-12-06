# How to Use the Review Prompts

## Overview

Two review prompts have been created for comprehensive code review by Claude Opus 4.5 or similar advanced models:

1. **`REVIEW_PROMPT_FOR_OPUS.md`** - Comprehensive, detailed review (recommended)
2. **`REVIEW_PROMPT_CONCISE.md`** - Shorter, focused review (if token limits are a concern)

## Which Prompt to Use?

### Use the Comprehensive Prompt (`REVIEW_PROMPT_FOR_OPUS.md`) if:
- You have sufficient token budget
- You want thorough, detailed analysis
- This is your first review
- You want architecture recommendations

### Use the Concise Prompt (`REVIEW_PROMPT_CONCISE.md`) if:
- Token limits are a concern
- You need a quick focused review
- You've already done a comprehensive review and want a follow-up
- You're looking for critical issues only

## How to Submit for Review

### Option 1: Direct Prompt Submission

1. Copy the entire contents of `REVIEW_PROMPT_FOR_OPUS.md`
2. Paste into Claude Opus 4.5 or your chosen model
3. The model will need access to your codebase - either:
   - Upload the entire `crypto_bot` directory
   - Or provide file paths and the model can read them if it has access

### Option 2: Context-Aware Submission

If your model supports it, provide:
1. The review prompt
2. Access to the codebase (via file upload, repository link, or file paths)
3. Specific files mentioned in the prompt:
   - `main.py`
   - `core/event_bus.py`
   - `core/agent_base.py`
   - `exchanges/mock_exchange.py`
   - `exchanges/base.py`
   - `agents/crypto/funding_rate_agent.py`
   - `risk/circuit_breaker.py`
   - `risk/limits.py`
   - `simulation/pnl_calculator.py`
   - `config/settings.py`
   - `simulation/position_tracker.py`
   - `simulation/state_manager.py`

### Option 3: Incremental Review

For very large codebases, you can break it down:

1. **Phase 1:** Submit prompt + critical files only:
   - `main.py`
   - `exchanges/mock_exchange.py`
   - `risk/circuit_breaker.py`
   - `simulation/pnl_calculator.py`

2. **Phase 2:** Submit prompt + remaining core files:
   - `core/event_bus.py`
   - `core/agent_base.py`
   - `agents/crypto/funding_rate_agent.py`

3. **Phase 3:** Submit prompt + supporting files:
   - `config/settings.py`
   - `risk/limits.py`
   - `simulation/position_tracker.py`

## What to Expect from the Review

The review should provide:

1. **Executive Summary**
   - Overall risk assessment
   - Top critical issues
   - Top recommendations

2. **Detailed Findings**
   - For each issue: severity, location, description, impact, recommendation

3. **Priority Action Items**
   - Must fix before live trading
   - Should fix soon
   - Nice to have

4. **Architecture Recommendations**
   - Design improvements
   - Missing components
   - Scalability concerns

5. **Answers to Key Questions**
   - Is it safe for real money?
   - Worst-case failure scenarios
   - Missing critical features

## After Receiving the Review

1. **Categorize Issues:**
   - Create issues/tickets for each finding
   - Prioritize by severity
   - Assign to appropriate components

2. **Create Fix Plan:**
   - Start with Critical issues
   - Test fixes thoroughly
   - Re-validate after fixes

3. **Iterate:**
   - Fix critical issues
   - Re-run validation scripts
   - Consider follow-up review for fixed areas

4. **Document:**
   - Keep review results
   - Track fixes applied
   - Note any issues you disagree with (and why)

## Tips for Best Results

1. **Be Specific:** If you have particular concerns, add them to the prompt
2. **Provide Context:** Mention your deployment plans (capital size, strategies)
3. **Ask Follow-ups:** After initial review, ask specific questions about findings
4. **Iterate:** Don't expect one review to catch everything - do multiple passes

## Example Submission

```
[Copy entire REVIEW_PROMPT_FOR_OPUS.md contents here]

---

Additional Context:
- Planning to start with $5K capital
- Primary strategy: Funding rate arbitrage
- Will run 24/7 on VPS
- Need to know: Is this safe to run unattended?
```

## Next Steps After Review

Once you receive the review results:

1. Share the findings with me (the AI assistant)
2. I can help:
   - Prioritize fixes
   - Implement recommended changes
   - Create tests for identified issues
   - Refactor problematic code sections

## Integration with Validation

The review complements the validation scripts:
- **Validation scripts** (`phase0_validation.ps1`) test if things work
- **Code review** tests if things work correctly and safely

Both are needed before live trading!

