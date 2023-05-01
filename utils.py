from cognite.client import CogniteClient, ClientConfig
from msal import PublicClientApplication
from cognite.client.credentials import Token
import streamlit as st
import openai
from langchain.llms import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Contact Project Administrator to get these
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")

CDF_CLUSTER = "api"  # api, westeurope-1 etc
COGNITE_PROJECT = "petro-tech-staging"

BASE_URL = f"https://{CDF_CLUSTER}.cognitedata.com"
SCOPES = [f"https://{CDF_CLUSTER}.cognitedata.com/.default"]

AUTHORITY_HOST_URI = "https://login.microsoftonline.com"
AUTHORITY_URI = AUTHORITY_HOST_URI + "/" + TENANT_ID
PORT = 53000

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"


def authenticate_azure():

    app = PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY_URI)

    # interactive login - make sure you have http://localhost:port in Redirect URI in App Registration as type "Mobile and desktop applications"
    creds = app.acquire_token_interactive(scopes=SCOPES, port=PORT)
    return creds

@st.cache_resource
def get_client():
    '''Authenticate and return a CogniteClient instance'''
    creds = authenticate_azure()

    cnf = ClientConfig(client_name="document-extractor", project=COGNITE_PROJECT, credentials=Token(creds["access_token"]), base_url=BASE_URL)
    client = CogniteClient(cnf)
    return client

@st.cache_resource
def configure_llm():
    openai.api_type = "azure"
    openai.api_base = "https://openai-experiment.openai.azure.com/"
    openai.api_version = "2022-12-01"
    openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")

    return AzureOpenAI(deployment_name="document-parser", temperature=0, openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"), openai_api_base="https://openai-experiment.openai.azure.com/", max_tokens=1000)
