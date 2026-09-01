import os
import io
import base64
import hashlib
import mimetypes
import re

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def parse_length_to_px(length_str, dpi=300):
    match = re.match(r'^([\d.]+)(mm|cm|in|px|pt)?$', str(length_str).strip().lower())
    if not match:
        return None
    val = float(match.group(1))
    unit = match.group(2) or 'px'
    
    if unit == 'px':
        return int(val)
    elif unit == 'in':
        return int(val * dpi)
    elif unit == 'mm':
        return int((val / 25.4) * dpi)
    elif unit == 'cm':
        return int((val / 2.54) * dpi)
    elif unit == 'pt':
        return int((val / 72) * dpi)
    return int(val)

def process_image(val, project_dir, sys_vars, mapping_key, image_registry):
    """
    Processes an image path: resolves it, potentially resizes it,
    and returns a class name or a src attribute string.
    Returns: (class_attr_addition, src_attr)
    """
    norm_val = os.path.normpath(val)
    if norm_val.startswith(os.sep) or norm_val.startswith('/'):
        norm_val = norm_val.lstrip(os.sep + '/')
        
    full_path = os.path.abspath(os.path.join(project_dir, norm_val))
    abs_project_dir = os.path.abspath(project_dir)
    
    if not (val and full_path.startswith(abs_project_dir + os.sep) and os.path.isfile(full_path)):
        return "", f' src="{val}"'

    mime_type, _ = mimetypes.guess_type(full_path)
    if not mime_type or not mime_type.startswith('image/'):
        return "", f' src="{val}"'

    with open(full_path, 'rb') as img_f:
        img_data = img_f.read()
    
    # Image resizing logic to save space
    if HAS_PIL and mime_type in ('image/jpeg', 'image/png', 'image/webp'):
        try:
            max_w = None
            max_h = None
            
            # Check for specific asset size limits first
            asset_configs = sys_vars.get('$max_asset_size', [])
            if not isinstance(asset_configs, list):
                asset_configs = [asset_configs]
                
            for config_line in asset_configs:
                parts = [p.strip() for p in config_line.split(',')]
                if len(parts) >= 3 and parts[0] == mapping_key:
                    max_w = int(parts[1])
                    max_h = int(parts[2])
                    break
                    
            # If no specific asset size, fallback to max_image_size or page dimensions
            if not max_w or not max_h:
                max_dim_conf = sys_vars.get('$max_image_size')
                if max_dim_conf and str(max_dim_conf).strip().isdigit():
                    max_w = max_h = int(str(max_dim_conf).strip())
                else:
                    dpi = int(sys_vars.get('$dpi', 300))
                    w_px = parse_length_to_px(sys_vars.get('$page_width', '210mm'), dpi)
                    h_px = parse_length_to_px(sys_vars.get('$page_height', '297mm'), dpi)
                    max_w = max_h = max(w_px, h_px) if (w_px and h_px) else 2480
                    
            if max_w and max_h:
                img = Image.open(io.BytesIO(img_data))
                if img.width > max_w or img.height > max_h:
                    # Using thumbnail maintains aspect ratio and only shrinks
                    img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                    
                    out_io = io.BytesIO()
                    fmt = img.format if img.format else ('PNG' if mime_type == 'image/png' else 'JPEG')
                    # Ensure mode is RGB if saving as JPEG
                    if fmt == 'JPEG' and img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                        
                    img.save(out_io, format=fmt, quality=85, optimize=True)
                    img_data = out_io.getvalue()
        except Exception as e:
            print(f"Warning: Failed to resize image {val}: {e}")
            
    img_hash = hashlib.md5(img_data).hexdigest()
    
    # Watch mode: save to cache directory, return URL path
    is_watch = sys_vars.get('_is_watch', False)
    if is_watch:
        cache_dir = os.path.join(project_dir, 'export', '.imgcache')
        os.makedirs(cache_dir, exist_ok=True)
        ext = os.path.splitext(full_path)[1].lower()
        cache_name = f"{img_hash[:12]}{ext}"
        cache_path = os.path.join(cache_dir, cache_name)
        if not os.path.exists(cache_path):
            with open(cache_path, 'wb') as f:
                f.write(img_data)
        return "", f' src=".imgcache/{cache_name}"'
    
    if img_hash not in image_registry:
        b64_str = base64.b64encode(img_data).decode('utf-8')
        class_name = f"b64img-{img_hash[:8]}"
        image_registry[img_hash] = {
            'class_name': class_name,
            'data_uri': f"data:{mime_type};base64,{b64_str}"
        }
    class_name = image_registry[img_hash]['class_name']
    
    return f' {class_name}', ""
