import streamlit as st
from utils import get_client, configure_llm
import os
from dotenv import load_dotenv
from extractor import DocumentParser

load_dotenv()

# Render Streamlit page
st.title("Document Extractor")
# st.markdown(
#     "This AI Sales Strategist helps sellers create a pre-call worksheet to help them prepare for their customer meeting. It is based on Command of the Message framework that is standard globally at Cognite."
# )

client = get_client()
    
llm = configure_llm()
    
project = st.text_input('Project', value='petro-tech-staging')
space_ext_id = st.text_input('Space External ID', value='Document_Extraction')
version = st.text_input('Data Model Version', value=1)
schema_id = st.selectbox(
    'Select a schema',
    'Pump, Compressor, Instrument'.split(', '))

extractor = DocumentParser(client, llm, project, schema_id, space_ext_id, version)

if st.button('Show Schema'):
    schema = extractor.get_schema()
    st.write(schema)
    
file_location = st.radio(

    "File Location",

    ('Local','In CDF'))

if file_location == 'Local':
    if schema_id == 'Pump':
        files = os.listdir('pump_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file = os.path.join('pump_data_sheets', file)
        
    elif schema_id == 'Compressor':
        files = os.listdir('compressor_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file = os.path.join('compressor_data_sheets', file)
    
    elif schema_id == 'Instrument':
        files = os.listdir('instrument_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file = os.path.join('instrument_data_sheets', file)
    
else:
    file_external_id = st.text_input('File ID', value='')
    res = client.files.retrieve(id=int(file_external_id))
    st.write(res)
    
file_type = st.radio(

    "File Type",

    ('single','multiple'))

if file_type=='multiple':
    page_min = int(st.text_input('Page Min', value=1))
    page_max = int(st.text_input('Page Max', value=10))
    
    
if st.button('Extract Data From Document'):
    if file_type=='single':
        with st.spinner('Executing...'):
            extractor.document_extraction(file, method="single")
        st.write('Completed!')
    elif file_type=='multiple':
        with st.spinner('Executing...'):
            extractor.document_extraction(file, method="multiple", page_min=page_min, page_max=page_max)
        st.write('Completed!')
        
# if st.button('See prompt'):
    st.write(extractor.upload_to_dm_body)
    st.write(extractor.type_remap)

# Using object notation
