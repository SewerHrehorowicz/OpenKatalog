def get_value_by_path(data, path):
    """Safely retrieves a value from a nested dictionary using dot notation."""
    if not isinstance(data, dict):
        return None
    keys = path.split('.')
    val = data
    for key in keys:
        if isinstance(val, dict) and key in val:
            val = val[key]
        else:
            return None
    return val

def resolve_mapping_value(context, global_data, sys_vars, m):
    """Resolves a mapping string against context, global data, and sys vars."""
    if m.startswith('$'):
        return sys_vars.get(m)
        
    val = get_value_by_path(context, m)
    if val is None:
        val = get_value_by_path(global_data, m)
        
    return val
