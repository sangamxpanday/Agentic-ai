from langgraph.graph import StateGraph, START, END 
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from dotenv import load_dotenv
import sqlite3
import requests 

load_dotenv()

llm = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.1-70B-Instruct",
    task="conversational",
    temperature=0.1,
)

chat_model = ChatHuggingFace(llm=llm)

search_tool = DuckDuckGoSearchRun()

@tool 
def calculator(first_number: float, second_number: float, operation: str) -> dict:
    """Performs basic arithmetic operations on two numbers.
    Args:
        first_number (float): The first number.
        second_number (float): The second number.
        operation (str): The arithmetic operation to perform.   
        returns:
        dict: A dictionary containing the result of the operation or an error message."""
    try:
        if operation == 'add':
            return {'result': first_number + second_number}
        elif operation == 'subtract':
            return {'result': first_number - second_number}
        elif operation == 'multiply':
            return {'result': first_number * second_number}
        elif operation == 'divide':
            if second_number != 0:
                return {'result': first_number / second_number}
            else:
                return {'error': 'Cannot divide by zero'}
        else:
            return {'error': 'Invalid operation'}
    except Exception as e:
        return {'error': str(e)}
    
@tool
def get_stock_price(symbol: str) -> dict:
    """"Fetch the current stock price for a given symbol using the Alpha Vantage API.
    Args:
        symbol (str): The stock symbol to fetch the price for.
    Returns:
        dict: A dictionary containing the stock price or an error message.
    """
    ALPHA_VANTAGE_API_KEY = "3QZR8BL9SAEETTZ7"
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
    r = requests.get(url)
    return r.json()

tools = [search_tool, calculator, get_stock_price]
llm_with_tools = chat_model.bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
    """LLm node that may answer or call tools"""
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    return {'messages': [response]}

tool_node = ToolNode(tools)

conn = sqlite3.connect(database = 'langgraph.db', check_same_thread=False)
checkpointer= SqliteSaver(conn = conn)

graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile(checkpointer=checkpointer)

def retreieve_all_threads():
    """Retrieves all threads from the database."""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)
