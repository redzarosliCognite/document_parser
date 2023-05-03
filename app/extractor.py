from difflib import SequenceMatcher
import os
from typing import Literal
import pdfplumber
import pandas as pd
import json
# from langchain.callbacks import get_openai_callback
from tqdm import tqdm
import io

class DocumentParser:
    def __init__(self, client, project, data_model, space, version, llm=None):
        self.client = client
        self.project = project
        self.data_model = data_model
        self.space = space
        self.version = version
        self.page_num = False
        self.llm = llm
        self.file_path = None
        self.file_id = None
        
        self.get_data_model()
 
    def _similar(self, a, b):
        return SequenceMatcher(None, a, b).ratio()
    
    def get_data_model(self):
        body = {
            "items": [
                {
                    "externalId": self.data_model,
                    "space": self.space,
                    "version": self.version
                }
            ]
        }
        res = self.client.post(f'/api/v1/projects/{self.project}/models/datamodels/byids', json=body)
        res = res.json()
        self.data_model = res
                
        self.views = [view['externalId'] for view in self.data_model['items'][0]['views']]
                
    def get_pages(self, number_pages=2):
        schema_keys = list(self.schema.keys())
        if self.file_path is not None:
            with pdfplumber.open(self.file_path) as pdf:
                all_pages=[]
                for idx,__ in enumerate(pdf.pages):
                    text=pdf.pages[idx].extract_text()
                    all_pages.append(text)
        else:
            file_bytes = self.client.files.download_bytes(id=self.file_id)
            data=io.BytesIO(file_bytes)
            with pdfplumber.open(data) as pdf:
                all_pages=[]
                for idx,__ in enumerate(pdf.pages):
                    text=pdf.pages[idx].extract_text()
                    all_pages.append(text)


        df = []
        for key in schema_keys:
            res = []
            for page_idx, page in enumerate(all_pages):
                for i in range(len(page)-len(key)):
                    subset = page[i:i+len(key)]
                    res.append({'key': key, 'section': subset, 'score':self._similar(key, subset), 'index': i, 'page': page_idx})
                
            sub_df = pd.DataFrame(data=res).sort_values('score', ascending=False)
                
            df.append(sub_df)
            
        df = pd.concat(df)
        df = df.sort_values('score', ascending=False)
        
        df_sum = df.groupby('page').sum(numeric_only=True)
        df_sum = df_sum.sort_values('score', ascending=False)
        self.pages_index = df_sum.index.tolist()[:number_pages]
        pages = [all_pages[i] for i in self.pages_index]

        
        return '\n'.join(pages)
      
    def get_single_page(self, page_num):
        if self.file_path is not None:
            with pdfplumber.open(self.file_path) as pdf:
                page = pdf.pages[page_num-1]
                text = page.extract_text()
        else:
            file_bytes = self.client.files.download_bytes(id=self.file_id)
            data=io.BytesIO(file_bytes)
            with pdfplumber.open(data) as pdf:
                page = pdf.pages[page_num-1]
                text = page.extract_text()
                
        return text
        # return df
        
    def parse_prompt(self):
        if self.method == 'multiple':
            pages = self.get_single_page(self.page_num)
            pages = '    ' + pages.replace('\n', '\n    ')
          
        elif self.method == 'single':
            pages = self.get_pages(number_pages=2)
            pages = '    ' + pages.replace('\n', '\n    ')
          
        schema_string = json.dumps(self.schema)

        self.prompt = f""" 
Find the keys from the %SCHEMA% from the following %DOCUMENT%. The %DOCUMENT% starts from %START% and ends at %END%. The response should be STRICTLY a json response in the format of the %SCHEMA%. If you dont know the answer for a key in %SCHEMA% return with null.


%SCHEMA%

{schema_string}

%DOCUMENT%
%START%
{pages}
%END%

%YOUR RESPONSE%:
```json
        """
      
        return self.prompt
      
        
  
    def get_schema(self, schema_id):
        for view in self.data_model['items'][0]['views']:
            if view['externalId'] == schema_id:
                self.view_version = view['version']
                
        self.get_schema_body = {
            "items": [
                {
                    "externalId": schema_id,
                    "space": self.space,
                    "version": self.view_version
                }
            ]
        }
        res = self.client.post(f'/api/v1/projects/{self.project}/models/views/byids', json=self.get_schema_body)
        res = res.json()
        self.schema_res = res
        
        if res['items'] == []:
            print(self.get_schema_body)
            raise ValueError('Schema not found')
        
        schema = {}
        keys_remap = {}
        type_map = {
          "float64": float,
          "text": str,
        }
        
        type_remap = {}
        for property, values in res['items'][0]['properties'].items():
            if 'type' in values['type'].keys():
                key_type = values['type']['type']
                if key_type in type_map.keys():
                    unit = values.get('description', None)
                    if unit:
                        schema[f"{property}_[{unit}]"] = key_type
                        keys_remap[f"{property}_[{unit}]"] = property
                    else:  
                        schema[property] = key_type
                        keys_remap[property] = property
                    
                    type_remap[property] = type_map[key_type]
        
        self.keys_remap = keys_remap
        self.keys_remap_reverse = {v: k for k, v in keys_remap.items()}
        self.type_remap = type_remap
    
        
        return schema



    def upload_to_dm(self):
        if self.file_path is not None:
            filename = self.file_path.split('/')[-1].split('.')[0]
        else:
            filename = self.file_id
            
        if self.page_num:
            external_id = f"{filename}_{self.page_num}"
        else:
            external_id = filename

        keys = [self.keys_remap[key] for key in self.gpt_res.keys() if key!='prompt']
        values = list(self.gpt_res.values())
        tmp = dict(zip(keys, values))
        res = {}
        for key, value in tmp.items():
            if value == self.schema[self.keys_remap_reverse[key]]: # skip if response from GPT just returns types (i.e "text", "float", etc)
                print(key)
                print(value)
                continue
            try:
                value = self.type_remap[key](value)
                res[key] = value
            except ValueError:
                pass
            except TypeError:
                pass
            
        self.upload_to_dm_body = {
        "items": [
            {
            "instanceType": "node",
            "space": self.space,
            "externalId": external_id,
            "existingVersion": self.version,
            "sources": [
                {
                "source": {
                    "type": "view",
                    "space": self.space,
                    "externalId": self.schema_id,
                    "version": self.view_version
                },
                "properties": res
                }
            ]
            }
        ]
        }

        self.upload_res = self.client.post(f'/api/v1/projects/{self.project}/models/instances', json=self.upload_to_dm_body)
        
    def send_to_gpt(self, prompt):
        url = f"/api/v1/projects/{self.project}/context/gpt/chat/completions"
        json = {
            "messages": [
                {
                "role": "user",
                "content": prompt
                }
            ],
            "temperature": 0,
            "maxTokens": 1000
        }

        res = self.client.post(url, json=json)
        self.usage = res.json()['usage']
        
        return res.json()['choices'][0]['message']['content']
        
    def document_extraction_single(self, upload_to_dm):
        self.schema = self.get_schema(self.schema_id)

        prompt = self.parse_prompt()

        if self.llm != None:
            res = self.llm(prompt)
        else:
            res = self.send_to_gpt(prompt)

        self.raw_res = res
        res = json.loads(res)
        self.gpt_res = res

        if upload_to_dm:
            self.upload_to_dm()
        
    def document_extraction_multiple(self, page_min, page_max, upload_to_dm):
        self.schema = self.get_schema(self.schema_id)
        self.all_gpt_res = []
        for page_num in tqdm(range(page_min, page_max)):
            self.page_num = page_num

            prompt = self.parse_prompt()

            if self.llm != None:
                res = self.llm(prompt)
            else:
                res = self.send_to_gpt(prompt)
                
            res = json.loads(res)
            self.gpt_res = res
            res['prompt'] = prompt
            self.all_gpt_res.append(res)
            
            if upload_to_dm:
                self.upload_to_dm()
                
                    
        self.all_gpt_res = pd.DataFrame(self.all_gpt_res)
            
        
    def document_extraction(self, schema_id, method=Literal["single", "multiple"], file_path=None, file_id=None, page_min=None, page_max=None, upload_to_dm=True):
        self.schema_id = schema_id
        self.method = method 
        self.file_path = file_path
        self.file_id = file_id
        
        if self.file_path is None and self.file_id is None:
            raise Exception('Must provide either a file path or file id')
        
        if self.file_path is not None and self.file_id is not None:
            raise Exception('Must provide either a file path or file id, not both')
      
      
        if method == "single":
            if page_min!=None or page_max!=None:
                raise ValueError("page_min and page_max must not be specified for single page extraction")
            self.document_extraction_single(upload_to_dm)
        elif method == "multiple":
            if page_min==None or page_max==None:
                raise ValueError("page_min and page_max must be specified for multiple page extraction") 
            self.document_extraction_multiple(page_min, page_max, upload_to_dm)
        else:
            raise ValueError("Method must be either single or multiple")