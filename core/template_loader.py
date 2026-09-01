import os
from parser import parse_template

def load_templates(tpl_dir):
    templates = {}
    index_nodes = []
    
    if os.path.exists(tpl_dir):
        for fname in os.listdir(tpl_dir):
            if fname.endswith('.tpl'):
                res = parse_template(os.path.join(tpl_dir, fname))
                comp_name = os.path.splitext(fname)[0]
                if res['model']:
                    templates[res['model']] = res['nodes']
                templates[comp_name] = res['nodes']
                if fname == 'index.tpl':
                    index_nodes = res['nodes']
                    
    return templates, index_nodes
