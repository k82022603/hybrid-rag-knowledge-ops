# Sample Markdown Document

This is a sample markdown document for testing the document parser.

## Introduction

This document contains various elements commonly found in technical documentation:
- Headings at different levels
- Tables
- Images (references)
- Code blocks
- Lists

## Technical Specifications

| Feature | Specification | Status |
|---------|---------------|--------|
| Format | Markdown | Supported |
| Tables | Yes | Working |
| Images | Yes | Working |
| Code | Yes | Working |

## Code Example

Here is a sample code block:

```python
def parse_document(file_path: str) -> dict:
    """Parse a document and return structured data."""
    with open(file_path, 'r') as f:
        content = f.read()
    return {"content": content, "length": len(content)}
```

## Images

![Architecture Diagram](./images/architecture.png)

![Flow Chart](./images/flowchart.png)

## Conclusion

This sample document demonstrates the parsing capabilities of the DocumentParser.

### Summary Points

1. Multiple heading levels are supported
2. Tables are extracted and converted to structured format
3. Image references are captured
4. Code blocks are preserved

---

*Document Version: 1.0*
*Last Updated: 2026-01-25*
