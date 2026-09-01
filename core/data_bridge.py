import os

class DataBridge:
    """
    Abstract base class for Data Bridges.
    A Data Bridge is responsible for fetching data and shaping it into 
    the standardized dictionary structures (models_data, global_data) 
    that the OpenKatalog template renderer expects.
    """
    
    def fetch_data(self):
        """
        Must be implemented by subclasses.
        Should return a tuple: (models_data, global_data)
        """
        raise NotImplementedError("DataBridge subclasses must implement fetch_data()")


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
