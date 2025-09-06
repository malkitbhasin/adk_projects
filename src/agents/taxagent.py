"""
taxagent.py
Author: Anup Ojah
Date: 2025-07-18
==========================
==Tax Auditor Assistant==
==========================
This module is a specialized assistant designed to audit and explain tax amounts applied to business transactions
Workflow Overview:
1. Load config and credentials from .env
2. Register tools with the agent - AgenticRagTool, SQL Tool
3. Run the agent with user input and print response
"""
from oci.addons.adk import Agent, AgentClient
from oci.addons.adk.run.types import InlineInputLocation, ObjectStorageInputLocation
from oci.addons.adk.tool.prebuilt.agentic_sql_tool import AgenticSqlTool, SqlDialect, ModelSize
 
import os
from typing import Dict
from oci.addons.adk import Agent, AgentClient, tool
from pathlib import Path
from dotenv import load_dotenv
from src.toolkit.user_info import AccountToolkit
from oci.addons.adk.tool.prebuilt import AgenticRagTool
from src.prompt_engineering.topics.tax_auditor import prompt_Agent_Auditor
import logging

# ────────────────────────────────────────────────────────
# 1) bootstrap paths + env + llm
# ────────────────────────────────────────────────────────
logging.getLogger('adk').setLevel(logging.DEBUG)

THIS_DIR     = Path(__file__).resolve()
PROJECT_ROOT = THIS_DIR.parent.parent.parent

load_dotenv(PROJECT_ROOT / "config/.env")  # expects OCI_ vars in .env

# Set up the OCI GenAI Agents endpoint configuration
OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE")
OCI_PROFILE = os.getenv("OCI_PROFILE")
AGENT_EP_ID = os.getenv("AGENT_EP_ID")
AGENT_SERVICE_EP = os.getenv("AGENT_SERVICE_EP")
TAX_AGENT_KB_ME_ID = os.getenv("TAX_AGENT_KB_ME_ID")
TAX_AGENT_KB_BUS_ID = os.getenv("TAX_AGENT_KB_BUS_ID")
AGENT_REGION = os.getenv("AGENT_REGION")


INLINE_DATABASE_SCHEMA = '''
                        CREATE TABLE "ADMIN"."FLIGHT_DATA"
                        (   "FLIGHT_ID" NUMBER,
                            "AIRLINE" VARCHAR2(4000 BYTE) COLLATE "USING_NLS_COMP",
                            "FROM_LOCATION" VARCHAR2(4000 BYTE) COLLATE "USING_NLS_COMP",
                            "TO_LOCATION" VARCHAR2(4000 BYTE) COLLATE "USING_NLS_COMP",
                            "Date" TIMESTAMP (6),
                            "TIME_DEPARTURE" TIMESTAMP (6),
                            "TIME_ARRIVAL" TIMESTAMP (6),
                            "PRICE" NUMBER
                        )  DEFAULT COLLATION "USING_NLS_COMP" ;
                        '''
 
INLINE_TABLE_COLUMN_DESCRIPTION = '''
                        FLIGHTS table
                        - Each row in this table represents a flight
 
                        Columns:
                        "FLIGHT_ID" - The ID of the flight
                        "AIRLINE" - The airline company of the flight
                        "FROM_LOCATION" - The location where the flight is coming from in format City, Country (AIRPORT). i.e " New York, USA (JFK)"
                        "TO_LOCATION"- The destination of the flight in format City, Country (AIRPORT). i.e " New York, USA (JFK)"
                        "Date" - the date of the flight
                        "TIME_DEPARTURE" - the time the flight departs
                        "TIME_ARRIVAL" - the time the flight arrives
                        "PRICE"- the price of the flight
                         '''


# Instantiate a SQL Tool
sql_tool_with_inline_schema = AgenticSqlTool(
    name="Flight SQL Tool - Inline Schema",
    description="A NL2SQL tool that retrieves flight data",
    database_schema=InlineInputLocation(content=INLINE_DATABASE_SCHEMA),
    model_size=ModelSize.LARGE,
    dialect=SqlDialect.ORACLE_SQL,
    db_tool_connection_id="ocid1.databasetoolsconnection.oc1.us-chicago-1.amaaaaaayanwdzaauwk7ghmrkwojxspv2tcodt43geihocpe4yrendkxtyja",
    enable_sql_execution=True,
    enable_self_correction=True,
    # icl_examples=ObjectStorageInputLocation(namespace_name="namespace", bucket_name="bucket", prefix="_sql.icl_examples.txt"),
    table_and_column_description=InlineInputLocation(content=INLINE_TABLE_COLUMN_DESCRIPTION)
    # custom_instructions="instruction"
)

# ────────────────────────────────────────────────────────
# 2) Logic
# ────────────────────────────────────────────────────────
def agent_flow():

    client = AgentClient(
        auth_type="api_key",
        config=OCI_CONFIG_FILE,
        profile=OCI_PROFILE,
        region=AGENT_REGION
    )

    # instructions = prompt_Agent_Auditor # Assign the right topic
    # instructions = "You are an agent that retrieves answers from the policy documents and flight data. Also try to get answers from the policy document" # Assign the right topic
    instructions = "You are an agent that retrieves answers from the policy documents and flight data" # Assign the right topic
    # custom_instructions = (f"The RAG Tool with Tax knowledge about Meals and Entertaintment can be found under the knowledge base at {TAX_AGENT_KB_ME_ID} and Tax knowledge about Business can be found under the knowledge base at {TAX_AGENT_KB_BUS_ID} ")
    custom_instructions = (f"Use the tools to execute RAG search")
    # custom_instructions = (
    #     f"response with not more than 10 words. Hide any PHI information from sending back to the user")

    agent = Agent(
        client=client,
        agent_endpoint_id=AGENT_EP_ID,
        instructions=instructions,
        tools=[
            AgenticRagTool(knowledge_base_ids=[TAX_AGENT_KB_ME_ID], description=custom_instructions),
            #AccountToolkit()
            sql_tool_with_inline_schema
        ]
    )

    return agent


def setup_agent():

    agent = agent_flow()
    agent.setup()

    # This is a context your existing code is best at producing (e.g., fetching the authenticated user id)
    client_provided_context = "[Context: The logged in user ID is: user_123] "

    # # Handle the first user turn of the conversation
    # input = "Get user information for user logged in."
    # input = client_provided_context + " " + input
    # response = agent.run(input)
    # final_message = response.data["message"]["content"]["text"]
    # print(final_message)
    # # print(response.raw_data['message']['content']['text'])
    # # response.pretty_print()

    # # Handle the second user turn of the conversation
    # input = "Get more information about the organization he/she works for."
    # input = client_provided_context + " " + input
    # response = agent.run(input, session_id=response.session_id)
    # final_message = response.data["message"]["content"]["text"]
    # print(final_message)

    # Call the RAG Service
    input = "“give me policies on terms and conditions”"
    response = agent.run(input)
    final_message = response.data["message"]["content"]["text"]
    print(final_message)

    # Run the agent with a user message
    # input = "Find me flights from New York to Los Angeles"
    input = "get all rows from table flight_data"
    response = agent.run(input)
    response.pretty_print()
 
    # Print Response Traces
    response.pretty_print_traces()

if __name__ == "__main__":
    setup_agent()