import re

# Language-specific typography rules
# format: { language_code: [ (pattern_regex, replacement_string), ... ] }
TYPOGRAPHY_RULES = {
    'pl': [
        # Polish typography: prevent single-letter orphans (sierotki) at the end of lines.
        # Catches all single letters to cover common conjunctions (i, a, o, u, w, z) and edge cases.
        (re.compile(r'\b([a-zA-Z])\s+'), r'\1&nbsp;'),
        # Insert soft hyphens for long words (8+ chars) to allow proper line breaking
        (re.compile(r'\b(\w{8,})\b'), lambda m: insert_shy(m.group(1)))
    ],
    'cs': [
        # Czech typography is similar to Polish
        (re.compile(r'\b([a-zA-Z])\s+'), r'\1&nbsp;'),
        (re.compile(r'\b(\w{8,})\b'), lambda m: insert_shy(m.group(1)))
    ],
    'sk': [
        # Slovak typography
        (re.compile(r'\b([a-zA-Z])\s+'), r'\1&nbsp;'),
        (re.compile(r'\b(\w{8,})\b'), lambda m: insert_shy(m.group(1)))
    ],
    'en': [
        # English: soft hyphens for long words
        (re.compile(r'\b(\w{8,})\b'), lambda m: insert_shy(m.group(1)))
    ]
}

def insert_shy(word):
    """Insert soft hyphens every 4-5 characters for word breaking."""
    if len(word) < 8:
        return word
    result = []
    for i, ch in enumerate(word):
        result.append(ch)
        # Insert shy after every 4th character, but not at start or end
        if (i + 1) % 4 == 0 and i < len(word) - 2:
            result.append('&shy;')
    return ''.join(result)

def apply_typography(text, lang='en'):
    """
    Applies language-specific typography rules (like non-breaking spaces) to text.
    """
    if not text:
        return text
        
    # We might receive lang as a list if there are multiple config entries, so we take the first.
    if isinstance(lang, list):
        lang = lang[0]
        
    lang = str(lang).lower().strip()
    
    rules = TYPOGRAPHY_RULES.get(lang, [])
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
        
    return text

def apply_shy(text, lang='en'):
    """
    Apply only soft hyphen insertion for long words (no nbsp rules).
    """
    if not text:
        return text
        
    if isinstance(lang, list):
        lang = lang[0]
        
    lang = str(lang).lower().strip()
    
    # Apply only the soft hyphen rule (last rule in each language)
    rules = TYPOGRAPHY_RULES.get(lang, [])
    if rules:
        pattern, replacement = rules[-1]  # shy rule is always last
        text = pattern.sub(replacement, text)
        
    return text
