import os
import re

def parse_template(filepath):
    """Parses a .tpl file into an AST of nodes."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    
    root_nodes = []
    stack = []
    model = None
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if line.startswith('model:'):
            model = line.split(':', 1)[1].strip()
            continue
            
        indent_match = re.match(r'^[ \t]*', line)
        indent_level = len(indent_match.group(0))
        content = line.strip()
        
        mapping = None
        if '->' in content:
            content, mapping = content.split('->', 1)
            content = content.strip()
            mapping = mapping.strip()
            
        tag = 'div'
        classes = []
        id_val = None
        text_content = ""
        
        quote_match = re.search(r'"([^"]*)"$', content)
        if quote_match:
            text_content = quote_match.group(1)
            content = content[:quote_match.start()].strip()
            
        if content:
            parts = re.split(r'([.#@])', content)
            if parts[0] and not content.startswith('@'):
                tag = parts[0]
            i = 1
            while i < len(parts):
                if parts[i] == '@':
                    tag = parts[i+1]
                elif parts[i] == '.':
                    classes.append(parts[i+1])
                elif parts[i] == '#':
                    id_val = parts[i+1]
                i += 2
                
        node = {
            'tag': tag,
            'classes': classes,
            'id': id_val,
            'text': text_content,
            'mapping': mapping,
            'children': [],
            'indent': indent_level,
            'line': line_num,
            'file': filepath
        }
        
        while stack and stack[-1]['indent'] >= indent_level:
            stack.pop()
            
        if stack:
            stack[-1]['children'].append(node)
        else:
            root_nodes.append(node)
            
        stack.append(node)
        
    return {'model': model, 'nodes': root_nodes}