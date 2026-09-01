import os
from data_bridge import FileSystemDataBridge
from renderer import render_html
from styler import read_styles
from pdf_exporter import print_pdf
from template_loader import load_templates
from html_builder import build_final_html
import datetime

def load_config(project_dir):
    config_path = os.path.join(project_dir, 'config.cfg')
    config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip()
                        if key in config:
                            if not isinstance(config[key], list):
                                config[key] = [config[key]]
                            config[key].append(val)
                        else:
                            config[key] = val
    return config

def get_system_vars(config):
    now = datetime.datetime.now()
    sys_vars = {
        '$page_num': 0,
        '$date': now.strftime("%Y-%m-%d"),
        '$time': now.strftime("%H:%M"),
        '$datetime': now.strftime("%Y-%m-%d %H:%M"),
        '$year': now.strftime("%Y"),
        '$month': now.strftime("%m"),
        '$day': now.strftime("%d")
    }
    for k, v in config.items():
        sys_vars[f"${k}"] = v
    return sys_vars

def write_outputs(project_dir, minified_html, config, is_watch, force_pdf):
    export_dir = os.path.join(project_dir, 'export')
    os.makedirs(export_dir, exist_ok=True)
    
    project_name = os.path.basename(os.path.normpath(os.path.abspath(project_dir)))
    output_path = os.path.join(export_dir, f"{project_name}.html")
    
    export_target = config.get('export_target', 'both')
    if isinstance(export_target, list):
        export_target = export_target[0]
    export_target = export_target.lower()
    
    if force_pdf:
        export_target = 'pdf'
    elif is_watch:
        export_target = 'html'
    
    if export_target in ("both", "html"):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(minified_html)
        print(f"Success! Generated minified HTML at {output_path}")
    
    if export_target in ("both", "pdf") and not is_watch:
        pdf_path = os.path.join(export_dir, f"{project_name}.pdf")
        
        if export_target == "pdf":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minified_html)
                
        print_pdf(output_path, pdf_path)
        
        if export_target == "pdf":
            try:
                os.remove(output_path)
            except OSError:
                pass

def generate(project_dir, is_watch=False, force_pdf=False, no_bleed=False):
    """Main generator entry point."""
    data_dir = os.path.join(project_dir, 'data')
    tpl_dir = os.path.join(project_dir, 'templates')
    
    bridge = FileSystemDataBridge(data_dir)
    models_data, global_data = bridge.fetch_data()
    templates, index_nodes = load_templates(tpl_dir)
                    
    if not index_nodes:
        print("Error: no index.tpl found in templates/")
        return
        
    config = load_config(project_dir)
    
    if no_bleed:
        config['bleed'] = '0mm'
    
    if 'page_width' not in config or 'page_height' not in config:
        print("Error: Missing mandatory configuration. Both 'page_width' and 'page_height' must be defined in config.cfg.")
        return
        
    sys_vars = get_system_vars(config)
    image_registry = {}
    
    html_lines = render_html(index_nodes, {}, models_data, templates, project_dir, image_registry, 0, False, global_data, sys_vars)
    css_string = read_styles(project_dir)
    
    minified_html = build_final_html(html_lines, config, css_string, image_registry, is_watch, index_nodes)
    write_outputs(project_dir, minified_html, config, is_watch, force_pdf)

def diagnose(project_dir):
    """Runs a diagnosis to find missing or unused data."""
    data_dir = os.path.join(project_dir, 'data')
    tpl_dir = os.path.join(project_dir, 'templates')
    
    bridge = FileSystemDataBridge(data_dir)
    models_data, global_data = bridge.fetch_data()
    templates, index_nodes = load_templates(tpl_dir)
                    
    if not index_nodes:
        print(f"Diagnosis Failed: no index.tpl found in {tpl_dir}")
        return
        
    image_registry = {}
    render_html(index_nodes, {}, models_data, templates, project_dir, image_registry, 0, True, global_data)
    
    issues_found = False
    
    for model_name, items in models_data.items():
        if not items: continue
        print(f"\n--- Model: {model_name} ---")
        
        for item in items:
            identifier = item.get('name', item.get('title', item.get('__dir__', 'Unknown item')))
            meta = item.get('_metadata', {'used': set(), 'available': set(), 'missing': {}})
            
            missing_detailed = meta.get('missing', {})
            unused = meta['available'] - meta['used']
            
            if missing_detailed or unused:
                issues_found = True
                print(f"  Item: {identifier}")
                if missing_detailed:
                    print(f"    - Missing (expected by template):")
                    for k, location in missing_detailed.items():
                        print(f"        {k} (in {location})")
                if unused:
                    print(f"    - Unused (in data but ignored): {', '.join(unused)}")
                    
    if not issues_found:
        print("\nDiagnosis Complete: All data is perfectly mapped. No missing or unused data found.")
    else:
        print("\nDiagnosis Complete.")