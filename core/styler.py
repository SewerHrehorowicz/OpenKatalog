import os
import re

def read_styles(project_dir):
    """Reads and minifies all CSS files from the styles directory, embedding local url() assets as base64."""
    import base64
    import mimetypes
    
    styles_dir = os.path.join(project_dir, 'styles')
    if not os.path.exists(styles_dir):
        return ""
        
    css_content = []
    for fname in os.listdir(styles_dir):
        if fname.endswith('.css'):
            with open(os.path.join(styles_dir, fname), 'r', encoding='utf-8') as f:
                css_content.append(f.read())
                
    css = "".join(css_content)
    
    # Embed local resources referenced by url(...)
    def replace_url(match):
        url_path = match.group(1).strip('\'"')
        # Skip external or already embedded data
        if not url_path.startswith(('http://', 'https://', 'data:')):
            norm_url_path = os.path.normpath(url_path)
            if norm_url_path.startswith(os.sep) or norm_url_path.startswith('/'):
                norm_url_path = norm_url_path.lstrip(os.sep + '/')
                
            full_path = os.path.abspath(os.path.join(project_dir, norm_url_path))
            abs_project_dir = os.path.abspath(project_dir)
            
            if full_path.startswith(abs_project_dir + os.sep) and os.path.isfile(full_path):
                mime_type, _ = mimetypes.guess_type(full_path)
                if not mime_type:
                    if full_path.endswith('.ttf'):
                        mime_type = 'font/ttf'
                    elif full_path.endswith('.woff'):
                        mime_type = 'font/woff'
                    elif full_path.endswith('.woff2'):
                        mime_type = 'font/woff2'
                    elif full_path.endswith('.otf'):
                        mime_type = 'font/otf'
                    else:
                        mime_type = 'application/octet-stream'
                
                with open(full_path, 'rb') as asset_f:
                    b64_str = base64.b64encode(asset_f.read()).decode('utf-8')
                return f"url('data:{mime_type};base64,{b64_str}')"
        return match.group(0)

    css = re.sub(r'url\((.*?)\)', replace_url, css)
    
    # Simple CSS minification
    css = re.sub(r'/\*[\s\S]*?\*/', '', css) # remove comments
    css = re.sub(r'\s+', ' ', css) # collapse whitespace
    css = re.sub(r'\s*([\{\}\:\;\,])\s*', r'\1', css) # remove spaces around syntax
    return css.strip()
