from modules.ai_engine import ask_lmstudio

# =============================================
# ✍️ Auto Summary Module
# Generates Quick and Detailed summaries
# =============================================

def generate_quick_summary(text: str) -> str:
    """5 bullet point summary — good for last-minute revision."""
    words = text.split()
    context = " ".join(words[:3000])

    prompt = f"""Read the document below and write exactly 5 bullet point summary.

Format:
• [key point 1]
• [key point 2]
• [key point 3]
• [key point 4]
• [key point 5]

Rules:
- Each bullet must be 1-2 sentences max
- Cover the most important ideas
- Start immediately with •
- No intro text, no headings

Document:
{context}

Summary:"""

    return ask_lmstudio(prompt=prompt, context="")


def generate_detailed_summary(text: str) -> str:
    """Structured detailed summary with sections."""
    words = text.split()
    context = " ".join(words[:3000])

    prompt = f"""Read the document below and write a detailed structured summary.

Use this format:
## Overview
[2-3 sentences describing what this document is about]

## Key Topics
[List the main topics covered, one per line with a dash]

## Main Points
[The most important facts, concepts, or findings — 5-8 points]

## Key Terms
[Important terms or definitions mentioned — list them]

## Conclusion
[1-2 sentences summarizing the takeaway]

Rules:
- Be thorough but clear
- Use the document content only
- Start immediately with ## Overview

Document:
{context}

Detailed Summary:"""

    return ask_lmstudio(prompt=prompt, context="")
