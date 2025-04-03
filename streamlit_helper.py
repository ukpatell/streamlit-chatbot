# streamlit_helper.py
import streamlit as st
import json
import boto3 # type: ignore
from dotenv import load_dotenv # type: ignore
import os
import re


def get_knowledge_bases():
    """
    Retrieve all knowledge bases from AWS Bedrock
    """
    try:
        knowledge_bases = []
        # Using the bedrock client from session state
        paginator = st.session_state.bedrock_agent.get_paginator('list_knowledge_bases')
        
        # Iterate through all pages
        for page in paginator.paginate():
            for kb in page.get('knowledgeBaseSummaries', []):
                knowledge_bases.append({
                    'id': kb['knowledgeBaseId'],
                    'name': kb['name'],
                    'description': kb.get('description', 'No description available'),
                    'status': kb['status'],
                    'updated_at': kb['updatedAt']
                })
        
        return knowledge_bases
    except Exception as e:
        print(f"Error fetching knowledge bases: {str(e)}")  # Using print instead of st.sidebar.error
        return []

def create_augmented_prompt(original_prompt, passages):
    """
    Create an augmented prompt by combining the original prompt with relevant passages
    """
    context = "\n\n".join([f"Passage: {passage}" for passage in passages])
    augmented_prompt = f"""
    Context information is below.
    ---------------------
    {context}
    ---------------------
    Using the above context information, please answer the following question: {original_prompt}
    """
    return augmented_prompt
