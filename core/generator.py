import os
import re
import json
from data_bridge import FileSystemDataBridge
from renderer import render_html
from styler import read_styles
from pdf_exporter import print_pdf
from template_loader import load_templates
from html_builder import build_final_html
import datetime

def extract_template_variables(nodes, variables=None):
    """Recursively extract all variable names from template nodes."""
    if variables is None:
        variables = {}
    
    for node in nodes:
        mapping = node.get('mapping')
        if mapping:
            # Remove .shy() suffix if present
            clean_mapping = mapping[:-6] if mapping.endswith('.shy()') else mapping
            
            # Case 1: Simple variable (no dots, parens, spaces, $, or quotes)
            if (clean_mapping and 
                not clean_mapping.startswith('$') and 
                not clean_mapping.startswith('"') and
                '.' not in clean_mapping and
                '(' not in clean_mapping and
                ' ' not in clean_mapping):
                if clean_mapping not in variables:
                    variables[clean_mapping] = []
                variables[clean_mapping].append({
                    'file': os.path.basename(node.get('file', '')),
                    'line': node.get('line', 0)
                })
            # Case 2: Interpolated string - extract chain patterns like {artist.first_name}
            elif clean_mapping.startswith('"'):
                string_vars = re.findall(r'\{([^}]+)\}', clean_mapping)
                for var in string_vars:
                    var = var.strip()
                    if not var:
                        continue
                    # Store the full chain (e.g. artist.first_name)
                    if var not in variables:
                        variables[var] = []
                    variables[var].append({
                        'file': os.path.basename(node.get('file', '')),
                        'line': node.get('line', 0)
                    })
                    # Also store leaf identifiers so hover can resolve chains even
                    # if the exact chain wasn't indexed elsewhere.
                    for leaf in re.findall(r'\.([a-zA-Z_]\w*)', var):
                        if leaf not in variables:
                            variables[leaf] = []
                        variables[leaf].append({
                            'file': os.path.basename(node.get('file', '')),
                            'line': node.get('line', 0)
                        })
            # Case 3: Complex mapping - extract variable after 'as' keyword
            #           and variable names from method arguments
            else:
                as_match = re.search(r'\bas\s+([a-zA-Z_]\w*)\b', clean_mapping)
                if as_match:
                    as_var = as_match.group(1)
                    if as_var not in variables:
                        variables[as_var] = []
                    variables[as_var].append({
                        'file': os.path.basename(node.get('file', '')),
                        'line': node.get('line', 0)
                    })
                
                # Extract variable names from method arguments (e.g., sort_by(last_name, first_name))
                arg_matches = re.findall(r'\(([^)]+)\)', clean_mapping)
                for args in arg_matches:
                    for arg in re.split(r'\s*,\s*', args):
                        arg = arg.strip()
                        if re.match(r'^[a-zA-Z_]\w*$', arg) and not arg.startswith('$'):
                            if arg not in variables:
                                variables[arg] = []
                            variables[arg].append({
                                'file': os.path.basename(node.get('file', '')),
                                'line': node.get('line', 0)
                            })
        if node.get('children'):
            extract_template_variables(node['children'], variables)
    
    return variables

def build_usage_index(project_dir, templates, models_data, global_data):
    """Build an index of all template variables and their data file locations."""
    data_dir = os.path.join(project_dir, 'data')
    
    # Get all variables from all templates
    all_variables = {}
    for tpl_name, nodes in templates.items():
        extract_template_variables(nodes, all_variables)
    
    # Also extract from index nodes (they're stored separately)
    # Actually templates already includes index.tpl as 'index'
    
    # Build index: variable -> { exists, locations }
    usage_index = {}
    
    for var_name in all_variables:
        locations = find_variable_in_data(data_dir, var_name)
        usage_index[var_name] = {
            'exists': len(locations) > 0,
            'template_locations': all_variables[var_name],
            'data_locations': locations
        }
    
    return usage_index

def find_variable_in_data(data_dir, variableName):
    """Find all data file locations for a variable."""
    locations = []
    if not os.path.exists(data_dir):
        return locations
    
    for entry in os.listdir(data_dir):
        full_path = os.path.join(data_dir, entry)
        if os.path.isdir(full_path):
            # Search in model subdirectories
            locations.extend(_search_data_file(full_path, variableName, data_dir))
        elif entry == 'data.txt':
            _check_data_txt(full_path, variableName, data_dir, locations)
        elif not entry.startswith('.'):
            # Check global data files (e.g., cover.png, logo.svg, group_photo.jpg)
            base_name = os.path.splitext(entry)[0]
            if base_name.lower() == variableName.lower():
                rel_path = os.path.relpath(full_path, data_dir)
                locations.append({
                    'file': rel_path,
                    'type': 'global_file'
                })
    
    return locations

def _search_data_file(dir_path, variableName, data_dir):
    """Recursively search a directory for variable references."""
    locations = []
    for entry in os.listdir(dir_path):
        full_path = os.path.join(dir_path, entry)
        if os.path.isdir(full_path):
            locations.extend(_search_data_file(full_path, variableName, data_dir))
        elif entry == 'data.txt':
            _check_data_txt(full_path, variableName, data_dir, locations)
        elif not entry.startswith('.'):
            base_name = os.path.splitext(entry)[0]
            if base_name.lower() == variableName.lower():
                rel_path = os.path.relpath(full_path, data_dir)
                locations.append({
                    'file': rel_path,
                    'type': 'file'
                })
    return locations

def _check_data_txt(file_path, variableName, data_dir, locations):
    """Check a data.txt file for a variable key."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if ':' in line:
                    key = line.split(':', 1)[0].strip()
                    if key == variableName:
                        rel_path = os.path.relpath(file_path, data_dir)
                        locations.append({
                            'file': rel_path,
                            'type': 'key',
                            'line': line_num
                        })
    except (IOError, UnicodeDecodeError):
        pass

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
        '$day': now.strftime("%d"),
        '_page_nums': [],
        '_page_uses_num': []
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
    sys_vars['_is_watch'] = is_watch
    image_registry = {}

    html_lines = render_html(index_nodes, {}, models_data, templates, project_dir, image_registry, 0, False, global_data, sys_vars)
    css_string = read_styles(project_dir)

    page_nums = sys_vars.get('_page_nums', [])
    uses_num = sys_vars.get('_page_uses_num', [])
    page_nums = [num if uses else None for num, uses in zip(page_nums, uses_num)]
    minified_html = build_final_html(html_lines, config, css_string, image_registry, is_watch, index_nodes, page_nums)
    write_outputs(project_dir, minified_html, config, is_watch, force_pdf)
    
    # Build and write usage index for VS Code extension
    all_variables = {}
    for tpl_name, nodes in templates.items():
        extract_template_variables(nodes, all_variables)
    usage_index = bridge.get_usage_index(all_variables)
    
    # Store in cache directory (not versioned)
    cache_dir = os.path.join(project_dir, '.ok')
    os.makedirs(cache_dir, exist_ok=True)
    index_path = os.path.join(cache_dir, 'usage_index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(usage_index, f, indent=2)

def generate_usage_index_only(project_dir):
    """Lightweight command - rebuilds only the usage index without rendering."""
    data_dir = os.path.join(project_dir, 'data')
    tpl_dir = os.path.join(project_dir, 'templates')
    
    bridge = FileSystemDataBridge(data_dir)
    templates, index_nodes = load_templates(tpl_dir)
    
    if not templates:
        print("No templates found.")
        return
    
    all_variables = {}
    for tpl_name, nodes in templates.items():
        extract_template_variables(nodes, all_variables)
    
    usage_index = bridge.get_usage_index(all_variables)
    
    # Store in cache directory (not versioned)
    cache_dir = os.path.join(project_dir, '.ok')
    os.makedirs(cache_dir, exist_ok=True)
    index_path = os.path.join(cache_dir, 'usage_index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(usage_index, f, indent=2)
    
    print(f"Usage index rebuilt: {len(usage_index)} variables tracked")

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