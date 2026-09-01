import os
import re
import html
from typography import apply_typography
from utils import get_value_by_path, resolve_mapping_value
from image_processor import process_image

SELF_CLOSING = {'img', 'br', 'hr', 'input', 'meta', 'link'}

def handle_component_inclusion(node, context, models_data, templates, project_dir, image_registry, indent_level, diagnostics_mode, global_data, sys_vars):
    tag = node['tag']
    comp_context = context
    if node['mapping']:
        m = node['mapping']
        if m in context:
            comp_context = context[m]
        elif m in models_data:
            comp_context = models_data[m]
        elif m in global_data:
            comp_context = global_data[m]

    inner_html = []
    if isinstance(comp_context, list):
        for item in comp_context:
            inner_html.extend(render_html(templates[tag], item, models_data, templates, project_dir, image_registry, indent_level + 1, diagnostics_mode, global_data, sys_vars))
    else:
        inner_html.extend(render_html(templates[tag], comp_context, models_data, templates, project_dir, image_registry, indent_level + 1, diagnostics_mode, global_data, sys_vars))

    return inner_html

def process_missing_metadata(context, m, diagnostics_mode, node):
    if '_metadata' in context:
        if 'missing' not in context['_metadata']:
            context['_metadata']['missing'] = {}
        context['_metadata']['missing'][m] = f"{os.path.basename(node['file'])}:{node['line']}"
    if not diagnostics_mode:
        identifier = context.get('name', context.get('title', context.get('__dir__', 'Unknown item')))
        filename = os.path.basename(node['file'])
        print(f"Warning: Expected mapping '{m}' not found in data for '{identifier}' or global config.")
        print(f"         Requested in {filename}:{node['line']}")

def handle_loop_mapping(node, m, context, models_data, templates, project_dir, image_registry, indent_level, diagnostics_mode, global_data, sys_vars):
    inner_html = []

    # Parse the new syntax: `expression as variable`
    if ' as ' not in m:
        return inner_html

    expr, item_var = [part.strip() for part in m.split(' as ', 1)]

    # Check if there are method calls in the expression
    methods = []
    if '.' in expr:
        parts = expr.split('.')
        col_name = parts[0]
        methods = parts[1:]
    else:
        col_name = expr

    if '_metadata' in context:
        context['_metadata']['used'].add(col_name)

    items = context.get(col_name)
    if items is None and col_name in models_data:
        items = models_data[col_name]

    if items is None:
        list_props = [k for k, v in context.items() if isinstance(v, list) and k != 'classes']
        if len(list_props) == 1:
            fallback_key = list_props[0]
            items = context[fallback_key]
            if '_metadata' in context:
                context['_metadata']['used'].add(fallback_key)
        else:
            items = []

    chunk_size = 1

    # Process modifiers
    for method in methods:
        if method.startswith('sort_by(') and method.endswith(')'):
            sort_args = [arg.strip() for arg in method[len('sort_by('):-1].split(',')]
            reverse_sort = False
            if len(sort_args) > 0 and sort_args[-1].lower() in ('desc', 'asc'):
                order = sort_args.pop().lower()
                reverse_sort = (order == 'desc')
            if sort_args:
                items = sorted(items, key=lambda x: tuple(str(get_value_by_path(x, k) or "").lower() for k in sort_args), reverse=reverse_sort)
        elif method.startswith('chunk(') and method.endswith(')'):
            chunk_arg = method[len('chunk('):-1].strip()
            if chunk_arg.isdigit():
                chunk_size = int(chunk_arg)

    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)] if chunk_size > 0 else []

    has_chunk_method = any(m.startswith('chunk(') for m in methods)

    for chunk in chunks:
        # If chunk() was explicitly called, pass the list. Otherwise, pass the single item.
        val = chunk if has_chunk_method else chunk[0]

        child_ctx = {**context, item_var: val}
        inner_html.extend(render_html(node['children'], child_ctx, models_data, templates, project_dir, image_registry, indent_level + 1, diagnostics_mode, global_data, sys_vars))

    return inner_html

def handle_scalar_mapping(node, m, context, global_data, sys_vars, diagnostics_mode):
    if m.startswith('"') and m.endswith('"'):
        val = m[1:-1]
        # Check if $page_num is referenced in the string
        if '$page_num' in val:
            _increment_page_num(sys_vars)
        def replace_var(match):
            var_name = match.group(1)
            if var_name.startswith('$'):
                return str(sys_vars.get(var_name, ""))

            if '_metadata' in context:
                context['_metadata']['used'].add(var_name.split('.')[0])

            v = resolve_mapping_value(context, global_data, sys_vars, var_name)
            if v is None:
                process_missing_metadata(context, var_name, diagnostics_mode, node)
                v = ""
            return str(v)

        return re.sub(r'\{([^}]+)\}', replace_var, val)
    else:
        if m == '$page_num.restart()':
            sys_vars['$page_num'] = 0
            return ""
        if m == '$page_num':
            _increment_page_num(sys_vars)
            return str(sys_vars['$page_num'])
        if '_metadata' in context and not m.startswith('$'):
            context['_metadata']['used'].add(m.split('.')[0])

        val = resolve_mapping_value(context, global_data, sys_vars, m)
        if val is None:
            process_missing_metadata(context, m, diagnostics_mode, node)
            val = ""

    return str(val)


def _increment_page_num(sys_vars):
    """Increment $page_num and record it for the current page."""
    sys_vars['$page_num'] += 1
    page_idx = sys_vars.get('_page_index', 0)
    if sys_vars.get('_page_nums') is not None and page_idx < len(sys_vars['_page_nums']):
        sys_vars['_page_nums'][page_idx] = sys_vars['$page_num']
    _mark_page_num_used(sys_vars)


def _mark_page_num_used(sys_vars):
    """Mark the current page as using $page_num."""
    if sys_vars.get('_page_uses_num'):
        sys_vars['_page_uses_num'][-1] = True

def render_html(nodes, context, models_data, templates, project_dir, image_registry, indent_level=0, diagnostics_mode=False, global_data=None, sys_vars=None):
    """Recursively renders AST nodes into HTML strings, completely structure-agnostic."""
    if global_data is None:
        global_data = {}
    if sys_vars is None:
        import datetime
        now = datetime.datetime.now()
        sys_vars = {
            '$page_num': 0, # Starts at 0, increments on first .page
            '$date': now.strftime("%Y-%m-%d"),
            '$time': now.strftime("%H:%M"),
            '$datetime': now.strftime("%Y-%m-%d %H:%M"),
            '$year': now.strftime("%Y"),
            '$month': now.strftime("%m"),
            '$day': now.strftime("%d")
        }
        sys_vars['_page_nums'] = []
        sys_vars['_page_uses_num'] = []
        sys_vars['_is_watch'] = False

    html_lines = []
    indent_str = "  " * indent_level

    for node in nodes:
        tag = node['tag']
        classes = node['classes']
        classes_str = ' '.join(classes)
        class_attr = f' class="{classes_str}"' if classes_str else ''
        id_attr = f' id="{node["id"]}"' if node['id'] else ''

        # Track page index for every .page element
        if 'page' in classes:
            sys_vars['_page_index'] = sys_vars.get('_page_index', -1) + 1
            sys_vars['_page_nums'].append(None)
            sys_vars['_page_uses_num'].append(False)

        text_content = node['text']
        src_attr = ''
        
        inner_html = []
        
        # 1. Component inclusion (if tag is a known template)
        if tag in templates:
            html_lines.extend(handle_component_inclusion(node, context, models_data, templates, project_dir, image_registry, indent_level, diagnostics_mode, global_data, sys_vars))
            continue

        if node['mapping']:
            m = node['mapping']

            # Check for conditional mapping: 'if var' or 'if not var'
            if m.startswith('if '):
                condition = m[3:].strip()
                invert = False
                if condition.startswith('not '):
                    invert = True
                    condition = condition[4:].strip()

                val = resolve_mapping_value(context, global_data, sys_vars, condition)

                is_truthy = bool(val)
                if invert:
                    is_truthy = not is_truthy

                if not is_truthy:
                    continue  # Skip rendering this node and its children completely

                # If truthy, the node renders normally, but we clear `m` so it isn't treated as a scalar mapping
                m = None

        if node['mapping'] and m:
            # 2. Loop mapping with chunking (e.g., 'artists.page_items:2' or 'artists.artist.sort_by(name):')
            if ' as ' in m:
                inner_html.extend(handle_loop_mapping(node, m, context, models_data, templates, project_dir, image_registry, indent_level, diagnostics_mode, global_data, sys_vars))

            # 3. Old Collection Mapping Fallback (e.g. 'artists')
            elif m in models_data and not context:
                model_tpl_nodes = templates.get(m, [])
                if not model_tpl_nodes and not diagnostics_mode:
                    print(f"Warning: Collection '{m}' found in data, but no '{m}.tpl' template found.")
                for item_data in models_data[m]:
                    inner_html.extend(render_html(model_tpl_nodes, item_data, models_data, templates, project_dir, image_registry, indent_level + 1, diagnostics_mode, global_data, sys_vars))

            # 4. Scalar mapping (e.g., 'photo', 'name', 'header')
            else:
                val = handle_scalar_mapping(node, m, context, global_data, sys_vars, diagnostics_mode)
                
                # Implicitly omit the entire element and its children if the mapped scalar value is empty
                if not val.strip():
                    continue
                    
                if tag == 'img':
                    add_class, new_src = process_image(val, project_dir, sys_vars, m, image_registry)
                    if class_attr:
                        class_attr = f'{class_attr[:-1]}{add_class}"'
                    elif add_class:
                        class_attr = f' class="{add_class.strip()}"'
                    src_attr = new_src
                else:
                    text_content = val
                    
        # Render children normally if not handled by a loop mapping
        if not (node['mapping'] and ' as ' in node['mapping']) and node['children']:
            inner_html.extend(render_html(node['children'], context, models_data, templates, project_dir, image_registry, indent_level + 1, diagnostics_mode, global_data, sys_vars))
            
        attr_str = class_attr + id_attr + src_attr
        
        # If node is completely invisible (no tag/class/id/text) but has a mapping (like an anonymous loop), 
        # just output its children without wrapping them in an empty div.
        is_invisible = (tag == 'div' and not classes and not id_attr and not text_content and not src_attr and node['mapping'])
        
        if is_invisible:
            html_lines.extend(inner_html)
            continue
            
        if tag in SELF_CLOSING:
            html_lines.append(f"{indent_str}<{tag}{attr_str} />")
        else:
            escaped_text = html.escape(str(text_content)) if text_content else ""
            escaped_text = escaped_text.replace('&lt;br&gt;', '<br>')
            escaped_text = escaped_text.replace('\\n', '<br>')
            
            # Apply language-specific typography rules
            lang = sys_vars.get('$lang', 'en') if sys_vars else 'en'
            escaped_text = apply_typography(escaped_text, lang)
            
            if inner_html or (not inner_html and escaped_text == ""):
                html_lines.append(f"{indent_str}<{tag}{attr_str}>")
                if escaped_text:
                    html_lines.append(f"{indent_str}  {escaped_text}")
                if inner_html:
                    html_lines.extend(inner_html)
                html_lines.append(f"{indent_str}</{tag}>")
            else:
                html_lines.append(f"{indent_str}<{tag}{attr_str}>{escaped_text}</{tag}>")
                
    return html_lines
