import os

class DataBridge:
    """
    Abstract base class for Data Bridges.
    
    A DataBridge translates from any data source into the standardized
    intermediate format that the OpenKatalog template renderer expects.
    
    The renderer and templates are completely decoupled from data storage.
    Whether data lives in files, PostgreSQL, MongoDB, or a REST API, the
    output format is always identical.
    
    Standard intermediate format:
        models_data = {
            "model_name": [              # e.g., "artists"
                {
                    "__dir__": "item_id",     # directory/name identifier
                    "key1": "value1",         # data fields
                    "key2": "value2",
                    "_metadata": {"used": set(), "available": set()}
                },
                ...
            ]
        }
        
        global_data = {
            "cover": "data/cover.png",    # global files/values
            "title": "Catalog Title",
            ...
        }
    """
    
    def fetch_data(self):
        """
        Must be implemented by subclasses.
        Should return a tuple: (models_data, global_data)
        in the standard intermediate format described above.
        """
        raise NotImplementedError("DataBridge subclasses must implement fetch_data()")
    
    def get_usage_index(self, template_variables):
        """
        Build a usage index for template variables.
        
        Args:
            template_variables: dict of {variable_name: [{file, line}, ...]}
                             extracted from templates.
        
        Returns:
            dict of {variable_name: {"exists": bool, "template_locations": [...], "data_locations": [...]}}
            
        Default implementation checks against fetch_data() output.
        Subclasses may override for more efficient implementation
        (e.g., SQL query for PostgreSQL).
        """
        models_data, global_data = self.fetch_data()
        usage_index = {}
        data_dir = getattr(self, 'data_root', None)
        
        for var_name, tpl_locations in template_variables.items():
            data_locations = []
            if data_dir:
                from generator import find_variable_in_data
                data_locations = find_variable_in_data(data_dir, var_name)
            usage_index[var_name] = {
                'exists': len(data_locations) > 0,
                'template_locations': tpl_locations,
                'data_locations': data_locations
            }
        
        return usage_index


class FileSystemDataBridge(DataBridge):
    """
    Concrete implementation of DataBridge that reads data from the local 
    file system directory structure.
    """
    
    def __init__(self, data_root):
        self.data_root = data_root

    def fetch_data(self):
        models = {}
        global_data = {}
        
        if not os.path.exists(self.data_root):
            return models, global_data
            
        global_txt = os.path.join(self.data_root, 'data.txt')
        if os.path.exists(global_txt):
            with open(global_txt, 'r', encoding='utf-8') as f:
                last_key = None
                for line in f:
                    if ':' in line:
                        key, val = line.split(':', 1)
                        global_data[key.strip()] = val.strip()
                        last_key = key.strip()
                    elif last_key and line.strip():
                        global_data[last_key] += "<br>" + line.strip()
                        
        for item_name in os.listdir(self.data_root):
            item_path = os.path.join(self.data_root, item_name)
            if os.path.isfile(item_path) and not item_name.endswith('.txt') and not item_name.startswith('.'):
                base_name = os.path.splitext(item_name)[0]
                if base_name not in global_data:
                    global_data[base_name] = f"data/{item_name}"
                        
        for model_name in os.listdir(self.data_root):
            model_path = os.path.join(self.data_root, model_name)
            if not os.path.isdir(model_path):
                continue
                
            models[model_name] = []
            for item_name in os.listdir(model_path):
                item_path = os.path.join(model_path, item_name)
                if not os.path.isdir(item_path):
                    continue
                    
                item_data = {'__dir__': item_name, '_metadata': {'used': set(), 'available': set()}}
                # Read text content
                data_txt = os.path.join(item_path, 'data.txt')
                if os.path.exists(data_txt):
                    with open(data_txt, 'r', encoding='utf-8') as f:
                        last_key = None
                        for line in f:
                            if ':' in line:
                                key, val = line.split(':', 1)
                                key = key.strip()
                                item_data[key] = val.strip()
                                item_data['_metadata']['available'].add(key)
                                last_key = key
                            elif last_key and line.strip():
                                item_data[last_key] += "<br>" + line.strip()
                                
                # Read lists (subdirectories) or single file fields
                for sub_name in os.listdir(item_path):
                    sub_path = os.path.join(item_path, sub_name)
                    if os.path.isdir(sub_path):
                        files = []
                        for fname in os.listdir(sub_path):
                            if not fname.startswith('.'):
                                # Construct relative path for HTML src
                                files.append(f"data/{model_name}/{item_name}/{sub_name}/{fname}")
                        item_data[sub_name] = files
                        item_data['_metadata']['available'].add(sub_name)
                    elif os.path.isfile(sub_path) and not sub_path.endswith('.txt') and not sub_path.startswith('.'):
                        # Support mapping direct files like photo.png -> photo
                        base_name = os.path.splitext(sub_name)[0]
                        item_data[base_name] = f"data/{model_name}/{item_name}/{sub_name}"
                        item_data['_metadata']['available'].add(base_name)
                        
                models[model_name].append(item_data)
                
        return models, global_data
