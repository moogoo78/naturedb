import random
import string

# Define the character sets based on the NOID specification.
# The XDIGIT_CHARS set is designed to be unambiguous, avoiding vowels and
# letters that can be easily confused (like 'l' or 'o').
XDIGIT_CHARS = "0123456789bcdfghjkmnpqrstvwxz"
DIGIT_CHARS = string.digits

def calculate_check_character(base_string: str) -> str:
    """
    Calculates the checksum character ('k') for a given NOID base string.

    The NOID checksum algorithm calculates a weighted sum of the ordinal
    positions of each character in the base string. The result is used to
    select a character from the extended digit set as the checksum.

    Args:
        base_string: The identifier string without the check character.

    Returns:
        The calculated single-character checksum.
    """
    total = 0
    # Enumerate from 1 to match the 1-based indexing of the algorithm
    for i, char in enumerate(base_string, 1):
        # All characters in the base string are looked up in the extended
        # character set to find their ordinal value for the calculation.
        ordinal = XDIGIT_CHARS.find(char)
        if ordinal == -1:
            # This case should be rare, assuming a valid base_string.
            raise ValueError(f"Character '{char}' not in XDIGIT character set for checksum calculation.")
        total += i * ordinal

    # The check character is the character at the resulting index
    checksum_index = total % len(XDIGIT_CHARS)
    return XDIGIT_CHARS[checksum_index]

def mint(template: str) -> str:
    """
    Mints a new identifier based on a flexible template string.

    The template defines the structure of the identifier.
    - 'd': a pure digit {0-9}
    - 'e': an "extended digit" {0-9, b-z without vowels}
    - 'k': a final checksum character (optional)

    Args:
        template: A string defining the identifier format (e.g., "reedeedk").
                  The 'r' for random is assumed and doesn't need to be included.

    Returns:
        A complete identifier string conforming to the template.
    """
    has_checksum = False
    mask = template

    # Ignore 'r' prefix for randomness, as it's the default behavior.
    if mask.startswith('r'):
        mask = mask[1:]

    if mask.endswith('k'):
        has_checksum = True
        mask = mask[:-1]  # Remove 'k' to get the base mask

    base_parts = []
    for char_type in mask:
        if char_type == 'e':
            base_parts.append(random.choice(XDIGIT_CHARS))
        elif char_type == 'd':
            base_parts.append(random.choice(DIGIT_CHARS))
        else:
            raise ValueError(f"Invalid character in template mask: '{char_type}'")

    base_string = "".join(base_parts)

    if has_checksum:
        check_char = calculate_check_character(base_string)
        return base_string + check_char
    else:
        return base_string
