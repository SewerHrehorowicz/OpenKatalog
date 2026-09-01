import re

def build_css_string(config, css_string, image_registry):
    width_str = config.get('page_width', '210mm')
    height_str = config.get('page_height', '297mm')
    bleed_str = config.get('bleed', '0mm')
    
    def parse_dim(s):
        m = re.match(r"([\d\.]+)([a-zA-Z]+)", str(s).strip())
        if m: return float(m.group(1)), m.group(2)
        return 0, 'mm'
        
    w_val, w_unit = parse_dim(width_str)
    h_val, h_unit = parse_dim(height_str)
    b_val, b_unit = parse_dim(bleed_str)
    
    if w_unit == b_unit and h_unit == b_unit and b_val > 0:
        total_width = f"{w_val + (b_val * 2)}{w_unit}"
        total_height = f"{h_val + (b_val * 2)}{h_unit}"
    else:
        total_width = width_str
        total_height = height_str
    
    root_vars = []
    for k, v in config.items():
        if isinstance(v, list):
            root_vars.append(f"--{k}: {v[0]};")
        else:
            root_vars.append(f"--{k}: {v};")
            
    root_css = f":root {{ {' '.join(root_vars)} }}\n" if root_vars else ""
    page_css = f"@page {{ size: {total_width} {total_height}; margin: 0; }}\n{root_css}"
        
    final_css = page_css + (css_string if css_string else "")
    
    if image_registry:
        img_css = [f".{info['class_name']} {{ content: url('{info['data_uri']}'); }}" for info in image_registry.values()]
        final_css += " " + " ".join(img_css) if final_css else " ".join(img_css)
        
    return final_css

def insert_into_head(html_lines, content):
    inserted = False
    for i, line in enumerate(html_lines):
        if '<head>' in line or '<head ' in line:
            html_lines.insert(i + 1, content)
            inserted = True
            break
            
    if not inserted:
        if html_lines and '<html' in html_lines[0]:
            html_lines.insert(1, f"<head>{content}</head>")
        else:
            html_lines.insert(0, f"<head>{content}</head>")

def build_final_html(html_lines, config, css_string, image_registry, is_watch, index_nodes):
    final_css = build_css_string(config, css_string, image_registry)
    
    insert_into_head(html_lines, '<meta charset="UTF-8">')
    
    if final_css:
        insert_into_head(html_lines, f"<style>{final_css}</style>")
    
    if index_nodes and index_nodes[0]['tag'] == 'html':
        html_lines.insert(0, "<!DOCTYPE html>")
        
    lang = config.get('lang', 'en')
    for i, line in enumerate(html_lines):
        if line.lstrip().startswith('<html') and 'lang=' not in line:
            html_lines[i] = line.replace('<html', f'<html lang="{lang}"', 1)
            break
            
    minified_html = "".join(line.strip() for line in html_lines)
        
    if is_watch:
        lr_script = '<script src="/livereload.js"></script>'
        if "</body>" in minified_html:
            minified_html = minified_html.replace("</body>", lr_script + "</body>")
        else:
            minified_html += lr_script
            
    return minified_html
