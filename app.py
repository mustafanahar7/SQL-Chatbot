import streamlit as st 
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from sqlalchemy import create_engine
import sqlite3
import os 


st.set_page_config("Langchain: Chat With SQL DB",page_icon="")
st.title("Langchain: Chat With SQL DB")

# st.sidebar.title("Setting")

sql_option = ["Select","Connect to sqlite 3","Connect to PostgreSQL DB"]
select_sql_option = st.sidebar.radio("Select the connection ",sql_option)

if sql_option.index(select_sql_option)==2:
    db_uri="Postgres"
    postgres_host = st.sidebar.text_input("Enter the SQL Host")
    postgres_user = st.sidebar.text_input("Enter the Username")
    postgres_pass = st.sidebar.text_input("Enter the Password",type='password')
    postgres_db = st.sidebar.text_input("Enter the DB Name")
elif sql_option.index(select_sql_option)==1:
    db_uri='Sqlite'
else:
    db_uri=None
    
if not db_uri:
    st.info("Please Enter the Database information and uri")

    
api_key = st.sidebar.text_input("Groq Api Key",type="password")   
if not api_key:
    st.info("Please Enter the Groq Api Key")

else:    
    ## select the different llm models 
    models = st.sidebar.selectbox("Select your model",['Gemma2-9b-It','Llama3-8b-8192','Llama3-70b-8192'])
    try:
        llm = ChatGroq(model=models,groq_api_key = api_key)
    except Exception as e:
        st.error(f"API Key Error {e}")
        st.stop()
    
       

@st.cache_resource(ttl="2h")
def configure_db(db_uri,host=None,user=None,password=None,db_name=None,sqlite_file_path=None):
    if db_uri=="Sqlite":
        st.info("Currently This Database Is Not Avalaible")
    
    
    elif db_uri=="Postgres":
        if not (host and user and password and db_name):
            st.error("Please fill the connection details ....")
            st.stop()
        return SQLDatabase(create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:5432/{db_name}"))
        
if db_uri=="Postgres":
    db = configure_db(db_uri , postgres_host , postgres_user , postgres_pass , postgres_db)
elif db_uri=="Sqlite":
    sqlite_file_path = st.sidebar.text_input("Enter the full SQLite DB file path (absolute path)")   
    db = configure_db(db_uri,sqlite_file_path=sqlite_file_path)
else:
    db=None 
    # st.info("Please select the Database Connection")
    
    

prompt = PromptTemplate.from_template("""
        You are an agent designed to interact with an SQL database.
        Given an input question, create a syntactically correct SQL query to run, then look at the results of the query and return the answer.

        You must always respond with the final answer in this format: Final Answer: <your_answer>

        Begin!

        Question: {input}
""")    
    
## Toolkit and agent
if db is not None:
    toolkit = SQLDatabaseToolkit(db=db,llm=llm)
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        handle_parsing_errors=True,
        agent_kwargs={"prompt": prompt}
    )
    

    if "messages" not in st.session_state or st.sidebar.button("Clear Chat History"):
        st.session_state['messages'] = [{"role":"assistant","content":"How Can I Help You ?"}]
        
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])
        
    user_query = st.chat_input(placeholder="Ask any question you want from db")

    if user_query:
        st.session_state.messages.append({"role":"user","content":user_query})
        st.chat_message("user").write(user_query)
        
        with st.chat_message("assistant"):
            streamlit_callbacks = StreamlitCallbackHandler(st.container())
            with st.spinner("Thinking"):
                # response = agent.run(user_query,callbacks=[streamlit_callbacks])
                response = agent.run(user_query)
                st.session_state.messages.append({"role":"assistant","content":response})
                st.write(response)
                
    # Add Close Connection button to close the database connection
    if st.sidebar.button("Close Connection"):
        if db:
            # Close the database connection if it exists
            st.session_state.pop("db", None)  # Remove from session state
            st.sidebar.success("Connection Closed Successfully")
            db = None  # Clear the db object

else:
    st.info("Please connect to a database first.")