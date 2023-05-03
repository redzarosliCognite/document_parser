import base64
from typing import Literal
from cognite.client import CogniteClient, ClientConfig
from msal import PublicClientApplication
from cognite.client.credentials import Token
import streamlit as st
import openai
# from langchain.llms import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Contact Project Administrator to get these
# Contact Project Administrator to get these
TENANT_ID = "d4f21b24-81a6-4563-af51-5d8c9b7301bf"
CLIENT_ID = "f4111639-51b2-45be-ba74-bdee364fde45"

CDF_CLUSTER = "api"  # api, westeurope-1 etc
COGNITE_PROJECT = "petro-tech-staging"

BASE_URL = f"https://{CDF_CLUSTER}.cognitedata.com"
SCOPES = [f"https://{CDF_CLUSTER}.cognitedata.com/.default"]

AUTHORITY_HOST_URI = "https://login.microsoftonline.com"
AUTHORITY_URI = AUTHORITY_HOST_URI + "/" + TENANT_ID
PORT = 53000

def get_client_redirect():

    creds = authenticate_azure()
    # cnf = ClientConfig(client_name="my-special-client", project=COGNITE_PROJECT, credentials=Token(creds["access_token"]), base_url=BASE_URL)
    cnf = ClientConfig(client_name="my-special-client", project=COGNITE_PROJECT, credentials=creds, base_url=BASE_URL)
    client = CogniteClient(cnf)
    return client

def authenticate_azure():

    app = PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY_URI)

    # interactive login - make sure you have http://localhost:port in Redirect URI in App Registration as type "Mobile and desktop applications"
    creds = app.acquire_token_interactive(scopes=SCOPES, port=PORT)
    return creds

@st.cache_resource
def get_client(token, cluster, project):
    '''Authenticate and return a CogniteClient instance'''
    
    BASE_URL = f"https://{cluster}.cognitedata.com"
    

    cnf = ClientConfig(client_name="document-extractor", project=project, credentials=Token(token), base_url=BASE_URL)
    client = CogniteClient(cnf)
    return client


# @st.cache_resource
# def configure_llm():
#     openai.api_type = "azure"
#     openai.api_base = "https://openai-experiment.openai.azure.com/"
#     openai.api_version = "2022-12-01"
#     openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")

#     return AzureOpenAI(deployment_name="document-parser", temperature=0, openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"), openai_api_base="https://openai-experiment.openai.azure.com/", max_tokens=1000)

def show_pdf(file_path=None, file_bytes=None, page_num=1, width=1000):
    if file_path != None:
        with open(file_path,"rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    else:
        base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
        
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#page={page_num}" width="{width}" height="800" type="application/pdf"></iframe>'
    
    return pdf_display