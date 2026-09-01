import re

# Language-specific typography rules
# format: { language_code: [ (pattern_regex, replacement_string), ... ] }
TYPOGRAPHY_RULES = {
    'pl': [
        # Polish typography: prevent single-letter orphans (sierotki) at the end of lines.
        # Catches all single letters to cover common conjunctions (i, a, o, u, w, z) and edge cases.
        (re.compile(r'\b([a-zA-Z])\s+'), r'\1&nbsp;')
    ],
    'cs': [
        # Czech typography is similar to Polish
        (re.compile(r'\b([a-zA-Z])\s+'), r'\1&nbsp;')
    ],
    'sk': [
        # Slovak typography
        (re.compile(r'\b([a-zA-Z])\s+'), r'\1&nbsp;')
    ]
}

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
