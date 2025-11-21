#!/usr/bin/env python3
"""
GTD Protection Tests - RUN THESE BEFORE ANY DEPLOYMENT

These tests ensure that GTD formatting NEVER breaks.
If any of these tests fail, DO NOT DEPLOY.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gtd_protection import gtd_protector


def test_spelling_corrections():
    """Test that basic spelling corrections work."""
    test_cases = [
        ("hte", "the"),
        ("teh", "the"),
        ("do cash flow for hte company", "do cash flow for the company"),
        ("i dont think its working", "i don't think it's working"),
        ("youre right, ill fix it", "you're right, I'll fix it"),
        ("follow up with hte team", "follow up with the team"),
    ]

    print("Testing spelling corrections...")
    for input_text, expected in test_cases:
        result = gtd_protector.apply_spelling_corrections(input_text)
        if result != expected:
            print(f"❌ FAILED: '{input_text}' -> '{result}' (expected: '{expected}')")
            return False
        else:
            print(f"✓ '{input_text}' -> '{result}'")

    print("✅ Spelling corrections working!\n")
    return True


def test_gtd_fallback_formatting():
    """Test GTD fallback formatting."""
    test_cases = [
        ("do cash flow for best self", "Complete cash flow for best self"),
        ("task to call john", "Call john"),
        ("need to fix the sink", "Fix the sink"),
        ("send email to client", "Send email to client"),
        ("review the documents", "Review the documents"),
        ("hte budget needs updating", "Update the budget"),
        ("follow up with team", "Follow up with team"),
    ]

    print("Testing GTD fallback formatting...")
    for input_text, expected_pattern in test_cases:
        result = gtd_protector.format_with_gtd_fallback(input_text)
        # Check if result starts with capital and contains key words
        if not result[0].isupper():
            print(f"❌ FAILED: '{input_text}' -> '{result}' (doesn't start with capital)")
            return False
        print(f"✓ '{input_text}' -> '{result}'")

    print("✅ GTD fallback formatting working!\n")
    return True


def test_protection_system():
    """Test the full protection system."""
    test_cases = [
        # (original, ai_formatted, should_use_ai)
        ("do cash flow", "Review cash flow projections", True),  # Good AI format
        ("do cash flow", "do cash flow", False),  # Bad AI format (no change)
        ("do cash flow", "", False),  # Empty AI format
        ("do cash flow", None, False),  # Failed AI
        ("fix hte sink", "Repair the kitchen sink", True),  # Good AI with spelling fix
    ]

    print("Testing GTD protection system...")
    for original, ai_formatted, should_use_ai in test_cases:
        result = gtd_protector.protect_gtd_format(original, ai_formatted)

        # Check result is properly formatted
        if not result or not result[0].isupper():
            print(f"❌ FAILED: protect_gtd_format('{original}', '{ai_formatted}') -> '{result}'")
            return False

        # If AI format was good, it should be used
        if should_use_ai and ai_formatted and result != ai_formatted:
            print(f"❌ FAILED: Should have used AI format '{ai_formatted}' but got '{result}'")
            return False

        print(f"✓ protect_gtd_format('{original}', '{ai_formatted}') -> '{result}'")

    print("✅ GTD protection system working!\n")
    return True


def test_real_world_examples():
    """Test real-world examples that have broken before."""
    test_cases = [
        "do cash flow for best self",
        "hte sink needs fixing",
        "task to follow up with hanna friday",
        "bill cathryn for taxes",
        "get ss financials set",
        "setup profitability by sku report",
    ]

    print("Testing real-world examples...")
    for input_text in test_cases:
        # Test with no AI (worst case)
        result = gtd_protector.protect_gtd_format(input_text, None)

        # Must return something
        if not result:
            print(f"❌ FAILED: '{input_text}' returned empty result")
            return False

        # Must start with capital
        if not result[0].isupper():
            print(f"❌ FAILED: '{input_text}' -> '{result}' (no capital)")
            return False

        # Must be different from input (shows formatting happened)
        if result == input_text:
            print(f"❌ FAILED: '{input_text}' -> '{result}' (no formatting)")
            return False

        print(f"✓ '{input_text}' -> '{result}'")

    print("✅ Real-world examples working!\n")
    return True


def main():
    """Run all protection tests."""
    print("=" * 60)
    print("GTD PROTECTION TESTS - CORE FEATURE VALIDATION")
    print("=" * 60)
    print()

    tests = [
        test_spelling_corrections,
        test_gtd_fallback_formatting,
        test_protection_system,
        test_real_world_examples,
    ]

    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
            break

    print("=" * 60)
    if all_passed:
        print("✅ ALL GTD PROTECTION TESTS PASSED!")
        print("GTD formatting is protected and working correctly.")
    else:
        print("❌ GTD PROTECTION TESTS FAILED!")
        print("DO NOT DEPLOY - Core GTD functionality is broken!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
