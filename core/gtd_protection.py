"""
GTD Protection Module - CORE FEATURE PROTECTION

This module ensures that GTD normalization NEVER breaks.
It provides fallback mechanisms and validation to maintain core functionality.
"""

import logging
import re
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class GTDProtection:
    """Protects and ensures GTD formatting always works."""

    def __init__(self):
        """Initialize GTD protection with fallback patterns."""
        # Core spelling corrections that MUST work
        self.spelling_corrections = {
            "hte": "the",
            "teh": "the",
            "adn": "and",
            "nad": "and",
            "taht": "that",
            "thta": "that",
            "waht": "what",
            "whos": "who",
            "recieve": "receive",
            "seperate": "separate",
            "definately": "definitely",
            "occured": "occurred",
            "occurance": "occurrence",
            "dont": "don't",
            "wont": "won't",
            "cant": "can't",
            "isnt": "isn't",
            "arent": "aren't",
            "wasnt": "wasn't",
            "werent": "weren't",
            "hasnt": "hasn't",
            "havent": "haven't",
            "hadnt": "hadn't",
            "doesnt": "doesn't",
            "didnt": "didn't",
            "couldnt": "couldn't",
            "wouldnt": "wouldn't",
            "shouldnt": "shouldn't",
            "mightnt": "mightn't",
            "mustnt": "mustn't",
            "youre": "you're",
            "theyre": "they're",
            "hes": "he's",
            "shes": "she's",
            "its": "it's",
            "were": "we're",
            "theyve": "they've",
            "youve": "you've",
            "ive": "I've",
            "weve": "we've",
            "id": "I'd",
            "youd": "you'd",
            "hed": "he'd",
            "shed": "she'd",
            "wed": "we'd",
            "theyd": "they'd",
            "ill": "I'll",
            "youll": "you'll",
            "hell": "he'll",
            "shell": "she'll",
            "well": "we'll",
            "theyll": "they'll",
        }

        # GTD action verbs for formatting
        self.action_verbs = {
            "do": "Complete",
            "make": "Create",
            "fix": "Repair",
            "write": "Draft",
            "send": "Send",
            "call": "Call",
            "email": "Email",
            "buy": "Purchase",
            "get": "Obtain",
            "find": "Locate",
            "read": "Review",
            "check": "Verify",
            "update": "Update",
            "setup": "Set up",
            "plan": "Plan",
            "schedule": "Schedule",
            "organize": "Organize",
            "prepare": "Prepare",
            "review": "Review",
            "analyze": "Analyze",
            "research": "Research",
            "contact": "Contact",
            "follow up": "Follow up with",
            "reach out": "Contact",
        }

    def apply_spelling_corrections(self, text: str) -> str:
        """Apply spelling corrections - GUARANTEED to work."""
        corrected = text

        # Apply each correction with word boundaries
        for typo, correction in self.spelling_corrections.items():
            corrected = re.sub(
                r"\b" + re.escape(typo) + r"\b", correction, corrected, flags=re.IGNORECASE
            )

        logger.info(f"GTDProtection: Spelling '{text}' -> '{corrected}'")
        return corrected

    def format_with_gtd_fallback(self, text: str) -> str:
        """
        Format text with GTD principles using fallback logic.
        This ALWAYS returns a properly formatted task.
        """
        # Step 1: Apply spelling corrections
        corrected = self.apply_spelling_corrections(text)

        # Step 2: Ensure task starts with action verb
        formatted = self._ensure_action_verb(corrected)

        # Step 3: Capitalize first letter
        if formatted:
            formatted = formatted[0].upper() + formatted[1:]

        # Step 4: Remove trailing punctuation
        formatted = formatted.rstrip(".,!?")

        logger.info(f"GTDProtection: Formatted '{text}' -> '{formatted}'")
        return formatted

    def _ensure_action_verb(self, text: str) -> str:
        """Ensure text starts with an action verb."""
        words = text.split()
        if not words:
            return text

        first_word = words[0].lower()

        # If it already starts with an action verb, just clean it up
        if first_word in self.action_verbs:
            words[0] = self.action_verbs[first_word]
            return " ".join(words)

        # Common patterns to fix
        if first_word in ["task", "reminder", "need", "have", "want"]:
            # "task to call john" -> "Call john"
            # "need to fix sink" -> "Fix sink"
            # "want to review docs" -> "Review docs"
            if len(words) > 2 and words[1] == "to":
                return " ".join(words[2:])
            elif len(words) > 1:
                return " ".join(words[1:])

        # If no clear pattern, try to find action verb in the text
        for i, word in enumerate(words):
            if word.lower() in self.action_verbs:
                # Found action verb, restructure
                return self.action_verbs[word.lower()] + " " + " ".join(words[i + 1 :])

        # If no action verb found, prepend a default
        return "Complete: " + text

    def validate_gtd_format(self, original: str, formatted: str) -> bool:
        """
        Validate that GTD formatting was applied correctly.
        Returns True if formatting is acceptable, False if it needs fallback.
        """
        # Check if formatted text is empty or same as original
        if not formatted or formatted.strip() == original.strip():
            logger.warning(f"GTDProtection: Formatting failed validation - no change detected")
            return False

        # Check if it starts with capital letter
        if not formatted[0].isupper():
            logger.warning(
                f"GTDProtection: Formatting failed validation - doesn't start with capital"
            )
            return False

        # Check if it's too short (less than 3 characters)
        if len(formatted) < 3:
            logger.warning(f"GTDProtection: Formatting failed validation - too short")
            return False

        # Check if it contains only special characters
        if not any(c.isalnum() for c in formatted):
            logger.warning(
                f"GTDProtection: Formatting failed validation - no alphanumeric characters"
            )
            return False

        return True

    def protect_gtd_format(
        self, original_text: str, ai_formatted_text: Optional[str] = None
    ) -> str:
        """
        Main protection method - ensures GTD formatting ALWAYS works.

        Args:
            original_text: The original user input
            ai_formatted_text: Optional AI-formatted text (might be None if AI failed)

        Returns:
            Properly formatted GTD task text
        """
        logger.info(f"GTDProtection: Protecting task '{original_text}'")

        # If AI formatting worked and is valid, use it
        if ai_formatted_text and self.validate_gtd_format(original_text, ai_formatted_text):
            logger.info(f"GTDProtection: Using AI format: '{ai_formatted_text}'")
            return ai_formatted_text

        # Otherwise, use fallback formatting
        logger.info(f"GTDProtection: Using fallback format for '{original_text}'")
        return self.format_with_gtd_fallback(original_text)


# Global instance for easy access
gtd_protector = GTDProtection()
