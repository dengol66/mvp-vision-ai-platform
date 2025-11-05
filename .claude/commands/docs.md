# /docs - Session Documentation Generator

Analyze the current conversation session and create a structured markdown document.

## Usage

```
/docs <target_directory>
```

**Arguments:**
- `target_directory`: Directory path where the document should be saved (e.g., `/docs/datasets`, `/docs/architecture`, `/docs/features`)

**Examples:**
```
/docs /docs/datasets
/docs /docs/architecture/decisions
/docs /docs/features/training
```

## Instructions for Claude

When this command is invoked:

1. **Analyze Current Session**
   - Identify the main topic/feature being discussed
   - Extract key decisions made
   - Capture technical implementation details
   - Note any alternatives considered and rejected
   - Include relevant code examples or configurations

2. **Determine Document Name**
   - Generate a descriptive name based on the topic (e.g., `dataset_split_strategy`, `logging_architecture`)
   - Use snake_case format
   - Keep it concise but descriptive (2-5 words)

3. **Create Timestamp Prefix**
   - Use current date and time from <env>
   - Format: `YYYYMMDD_HHMMSS` (e.g., `20251105_143022`)
   - If time is not available, use `YYYYMMDD` only
   - **IMPORTANT**: Use the ACTUAL date from <env> "Today's date" field - do not guess or use wrong dates

4. **Generate File Path**
   - Combine: `{target_directory}/{timestamp}_{document_name}.md`
   - Example: `/docs/datasets/20251105_143022_dataset_split_strategy.md`

5. **Document Structure**

   Use the following markdown template:

   ```markdown
   # [Document Title]

   **Date**: YYYY-MM-DD HH:MM
   **Status**: Draft | Proposed | Approved | Implemented
   **Related Issues**: [if applicable]

   ## Overview

   [Brief 2-3 sentence summary of what this document covers]

   ## Background / Context

   [Why this topic came up, what problem we're solving]

   ## Current State

   [What exists now, what we discovered during investigation]

   ## Proposed Solution / Decision

   [Main technical approach or architectural decision]

   ### Key Design Choices

   1. **Choice 1**
      - Rationale: ...
      - Trade-offs: ...

   2. **Choice 2**
      - Rationale: ...
      - Trade-offs: ...

   ## Implementation Plan

   ### Phase 1: [Name]
   - [ ] Task 1
   - [ ] Task 2

   ### Phase 2: [Name]
   - [ ] Task 1

   ## Technical Details

   ### Data Structures

   ```json
   {
     "example": "schema"
   }
   ```

   ### Code Examples

   ```python
   # Example implementation
   ```

   ## Alternatives Considered

   1. **Alternative 1**
      - Pros: ...
      - Cons: ...
      - Why rejected: ...

   ## Migration Path

   [How to transition from current state to new implementation]

   ## References

   - Related files: ...
   - Related docs: ...
   - External resources: ...

   ## Notes

   [Any additional context, open questions, or future considerations]
   ```

6. **Write the Document**
   - Use the Write tool to create the markdown file
   - Ensure all dates are accurate (check <env> "Today's date")
   - Use proper markdown formatting
   - Include code blocks with syntax highlighting
   - Keep language clear and concise

7. **Confirm to User**
   - Show the file path where document was saved
   - Provide a brief summary of what was documented

## Quality Checklist

Before writing the document, ensure:
- [ ] Date/time is accurate from <env>
- [ ] Filename uses snake_case
- [ ] Timestamp prefix is in YYYYMMDD_HHMMSS format
- [ ] Target directory exists or will be created
- [ ] Document covers key decisions and rationale
- [ ] Code examples are properly formatted
- [ ] Technical details are accurate and complete

## Important Notes

- **CRITICAL**: Always verify the date from <env> "Today's date" field - do NOT use placeholder dates or incorrect years
- If the target directory doesn't exist, create it
- If a file with the same name exists, append a number (e.g., `_v2.md`)
- Focus on capturing DECISIONS and RATIONALE, not just facts
- Include enough context for someone to understand the decision 6 months from now
