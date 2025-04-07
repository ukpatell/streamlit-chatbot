import streamlit as st
import json
import boto3 # type: ignore
from dotenv import load_dotenv # type: ignore
import os
import re
import streamlit_helper as helper
#load environment
load_dotenv()

#init aws client with env variables
if "client" not in st.session_state:
    try:
        session = boto3.Session(
            profile_name="XXXX",
            region_name="us-west-2")
        #init client
        bedrock_runtime = session.client('bedrock-runtime')
        bedrock = session.client('bedrock')
        bedrock_agent = session.client('bedrock-agent')
        bedrock_agent_runtime = session.client('bedrock-agent-runtime')
        st.session_state.bedrock = bedrock
        st.session_state.bedrock_runtime = bedrock_runtime
        st.session_state.bedrock_agent = bedrock_agent
        st.session_state.bedrock_agent_runtime = bedrock_agent_runtime
        st.session_state.messages = []

    except Exception as e:
        st.error(f"Failed to initialize AWS client: {str(e)}")
        st.info("Please ensure your AWS credentials are properly configured in .env")
        st.stop()



st.title("Chat with Bedrock")
st.caption("A simple chatbot that uses Amazon Bedrock")


st.sidebar.title("Configuration")

model = st.sidebar.selectbox("Model", ["Claude 3.5 Haiku", "Claude 3.5 Sonnet v2","Nova Pro"])
if model == "Claude 3.5 Haiku":
    st.sidebar.caption("Claude 3 Haiku is Anthropic's fastest, most compact model for near-instant responsiveness. It answers simple queries and requests with speed")
    model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

elif model == "Claude 3.5 Sonnet v2":
    st.sidebar.caption("he upgraded Claude 3.5 Sonnet is now state-of-the-art for a variety of tasks including real-world software engineering, agentic capabilities and computer use. ")
    model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"


elif model == "Nova Pro":
    st.sidebar.caption("Nova Pro is a multimodal understanding foundation model. It is multilingual and can reason over text, images and videos.")
    model_id = "us.amazon.nova-pro-v1:0"

# Add this in the sidebar section, after the model selection

st.sidebar.divider()
st.sidebar.subheader("RAG Configuration")

# Toggle for RAG
use_rag = st.sidebar.toggle("Enable RAG (Retrieval Augmented Generation)", value=False)

# Only show knowledge base selection if RAG is enabled
if use_rag:
    # Fetch available knowledge bases
    with st.spinner(text="Fetching knowledge bases...", show_time=True):
        knowledge_bases = helper.get_knowledge_bases()
        
    if knowledge_bases:
        # Create options list with None as first option
        kb_options = ["None"] + [
            f"{kb['name']} ({kb['id']})" 
            for kb in knowledge_bases 
            if kb['status'] == 'ACTIVE'
        ]
        
        selected_kb = st.sidebar.selectbox(
            "Select Knowledge Base",
            kb_options,
            help="Choose the knowledge base to augment the model's responses"
        )
        
        # If a knowledge base is selected, show its details
        if selected_kb != "None":
            selected_kb_id = selected_kb.split('(')[-1].rstrip(')')
            kb_info = next(kb for kb in knowledge_bases if kb['id'] == selected_kb_id)
            
            with st.sidebar.expander("Knowledge Base Details"):
                st.write(f"**Description:** {kb_info['description']}")
                st.write(f"**Status:** {kb_info['status']}")
                st.write(f"**Last Updated:** {kb_info['updated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            # RAG configuration options
            max_tokens = st.sidebar.number_input(
                "Max Tokens per Response",
                min_value=1,
                max_value=2048,
                value=512
            )
            
            relevance_threshold = st.sidebar.slider(
                "Relevance Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                help="Minimum relevance score for retrieved passages"
            )
    else:
        st.sidebar.warning("No knowledge bases found or error fetching knowledge bases")

# System Prompt
system_prompt = st.sidebar.text_area("System Prompt", value="You are a helpful assistant.")

# Temperature
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.5, 0.1)
# Max Tokens
max_tokens = st.sidebar.slider("Max Tokens", 10, 4096, 1024, 10)
# Top P
top_p = st.sidebar.slider("Top P", 0.0, 1.0, 0.5, 0.1)
# Stop Sequences
stop_sequences = st.sidebar.text_input("Stop Sequences", value="0")

# Clear Chat History
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# Initialize session state for messages if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []


# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# New Messages
if prompt := st.chat_input("Tell me something only an AI/ML Specialist would understand"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    # displaying our user prompt
    with st.chat_message("user"):
        st.markdown(prompt)

        # call bedrock knowledge base retrieve and generatre api
        if use_rag and selected_kb != "None":
            # RAG logic
            res = st.session_state.bedrock_agent_runtime.retrieve_and_generate(
                input={
                    'text': prompt
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'modelArn': model_id,
                        'knowledgeBaseId': selected_kb_id
                    }
                }
            )
            # Extract passages from the response
            print(res)
            # passages = [item['content']['text'] for item in res['output']]

            # Create an augmented prompt using the passages
            # augmented_prompt = helper.create_augmented_prompt(prompt, passages)

            # Update the prompt for the model
            # prompt = augmented_prompt
        
        # # converse api
        # res = st.session_state.bedrock_runtime.converse(
        #     modelId=model_id,
        #     messages=[
        #         {
        #             "role": "user",
        #             "content": [{
        #                 "text": prompt
        #                 }]
        #         }
        #     ],
        #     inferenceConfig={
        #         "maxTokens": max_tokens,
        #         "temperature": temperature,
        #         "topP": top_p,
        #         "stopSequences": [stop_sequences]
        #     },
        #     system=[
        #         {
        #             "text": system_prompt
        #         }
        #     ]
        # )
        # expandable response

        with st.expander("See response"):
            st.write(res['output']['text'])
            st.write("Sources:", res['citations'])

    # Extract the response text from the output structure
    if res and 'output' in res:
        # Get the message content from the output
        message = res['output']['text']
        
        # Extract text from the first content item
        # if
        #     response_text = message
        # else:
        #     response_text = "No response text found"

        # display response in message container
        with st.chat_message("assistant"):
            st.markdown(message)

        # add to chat history 
        st.session_state.messages.append({
            "role": "assistant", 
            "content": message
        })

        # display usage metrics
        if 'usage' in res:
            st.sidebar.write("Token Usage:", res['usage'])
