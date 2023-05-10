import base64
import streamlit as st
from utils import get_client, show_pdf
import os
from dotenv import load_dotenv
from extractor import DocumentParser

load_dotenv()
st.set_page_config(layout="wide")



# Render Streamlit page
st.title("Document Extractor")
# st.markdown(
#     "This AI Sales Strategist helps sellers create a pre-call worksheet to help them prepare for their customer meeting. It is based on Command of the Message framework that is standard globally at Cognite."
# )
    
    
# project = st.sidebar.text_input('Project', value='tp-otc-preprod')
# client_id = st.sidebar.text_input('Client ID', value='')
# tenant_id = st.sidebar.text_input('Tenant ID', value='')
# cluster = st.sidebar.text_input('Cluster', value='')

project = st.sidebar.text_input('Project', value='')
cluster = st.sidebar.text_input('Cluster', value='')
token = st.sidebar.text_input('Token', value='')

client = get_client(token, cluster, project)


space_ext_id = st.text_input('Space External ID', value='Document_Extraction')
data_model_id = st.text_input('Data Model', value='Document_Schemas')
version = st.text_input('Data Model Version', value=1)

extractor = DocumentParser(client, project, data_model_id, space_ext_id, version)


schema_id = st.selectbox(
    'Select a schema',
    extractor.views)


if st.button('Show Schema'):
    schema = extractor.get_schema(schema_id)
    st.write(schema)
    
file_location = st.radio(

    "File Location",

    ('In CDF', 'Local'))

file_path = None
file_id = None
file_content = None

if file_location == 'Local':
    if schema_id == 'Pump':
        files = os.listdir('localdev-pump_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file_path = os.path.join('localdev-pump_data_sheets', file)
        
    elif schema_id == 'Compressor':
        files = os.listdir('localdev-compressor_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file_path = os.path.join('localdev-compressor_data_sheets', file)
    
    elif schema_id == 'Instrument':
        files = os.listdir('localdev-instrument_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file_path = os.path.join('localdev-instrument_data_sheets', file)
        
    elif schema_id in ['PumpISO14224', 'PumpISO2']:
        files = os.listdir('localdev-pump_data_sheets')
    
        file = st.selectbox(
            'Select a file',
            files)
        
        file_path = os.path.join('localdev-pump_data_sheets', file)
    
else:
    file_external_id = st.text_input('File ID', value='')
    if file_external_id != '':
        try:
            res = client.files.retrieve(id=int(file_external_id))
            if res is None:
                st.write('File not in CDF')
            else:
                file_id = res.id
                file_content = client.files.download_bytes(id=file_id)
                st.write(res)
    
        except ValueError:
            raise ValueError('File ID has to be an integer')

if file_content is not None:
    pdf_display = show_pdf(file_bytes=file_content, width=1400)
    st.markdown(pdf_display, unsafe_allow_html=True)
    
# pdf_display = show_pdf(file_path)

file_type = st.radio(

    "File Type",

    ('Single Asset','Multiple Assets'))

if file_type=='Multiple Assets':
    page_start = int(st.text_input('Page Min', value=50))
    page_end = int(st.text_input('Page Max', value=60))
    
show_prompt = st.sidebar.checkbox('Show Prompt', value=False)
# upload_to_dm = st.sidebar.checkbox('Upload to DM', value=True)
upload_to_dm = True

if st.button('Extract Data From Document'):
    if file_type=='Single Asset':
        with st.spinner('Executing...'):
            extractor.document_extraction(schema_id, method="single", upload_to_dm=upload_to_dm, file_path=file_path, file_id=file_id)
        st.write('Completed!')
        
        col1, col2 = st.columns([3,1])


        pdf_display = show_pdf(file_path, page_num=extractor.pages_index[0])
        col1.markdown(pdf_display, unsafe_allow_html=True)

        col2.header("GPT Response")
        col2.write(extractor.gpt_res)
    
        extractor.upload_to_dm()
        
        # if upload_to_dm:
        #     st.write(extractor.upload_to_dm_body)
            
    elif file_type=='Multiple Assets':
        with st.spinner('Executing...'):
            extractor.document_extraction(schema_id, method="multiple", page_start=page_start, page_end=page_end, upload_to_dm=upload_to_dm,  file_path=file_path, file_id=file_id)
        st.write('Completed!')
        st.write(extractor.all_gpt_res)
        
        # if upload_to_dm:
        #     st.write(extractor.upload_to_dm_body)
        # else:
        #     st.write(extractor.gpt_res)
        
    
    if show_prompt:
        st.write(extractor.prompt)
    


# show_prompt = st.checkbox('See Prompt')
# if show_prompt:
#     st.write(extractor.prompt)
                    
# if st.button('See prompt'):

# Using object notation

# if st.button('Upload to Data Model'):
#     extractor.upload_to_dm()