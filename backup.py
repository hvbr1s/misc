import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, make_response, redirect, jsonify
from web3 import Web3
from llama_index import GPTSimpleVectorIndex, download_loader
from langchain.agents import initialize_agent, Tool, load_tools
from langchain.llms import OpenAI
from dotenv import load_dotenv
from eth_account.messages import encode_defunct
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.memory import ChatMessageHistory


load_dotenv()
history = ChatMessageHistory()

env_vars = [
    'OPENAI_API_KEY',
    'SERPAPI_API_KEY',
    'REDDIT_CLIENT_ID',
    'REDDIT_CLIENT_SECRET',
    'REDDIT_USER_AGENT',
    'REDDIT_USERNAME',
    'REDDIT_PASSWORD',
    'ALCHEMY_API_KEY',
]

os.environ.update({key: os.getenv(key) for key in env_vars})
os.environ['WEB3_PROVIDER'] = f"https://polygon-mumbai.g.alchemy.com/v2/{os.environ['ALCHEMY_API_KEY']}"

# Initialize web3
web3 = Web3(Web3.HTTPProvider(os.environ['WEB3_PROVIDER']))

# Initialize LLM
llm = OpenAI(temperature=0.5)

# Initialize chat
memory = ConversationBufferMemory()
conversation = ConversationChain(
    llm=llm, 
    verbose=True, 
    memory=memory
)


# Prepare UnstructuredReader Tool
UnstructuredReaderClass = download_loader("UnstructuredReader")
unstructured_reader = UnstructuredReaderClass()
documents = unstructured_reader.load_data(file=Path('/home/dan/langchain/langchain_bot/cal.txt'))

def start_query_func(index):
    def query_func(q):
        return index.query(q)
    return query_func

cal = Tool(
    name="Crypto Asset List",
    func=lambda q: start_query_func(index),
    description=f"A list of crypto coins and tokens supported in the latest version of Ledger Live. Check the list when asked if a token or coin is supported in Ledger Live.",
    )

# Prepare Reddit tool
subreddits = ['ledgerwallet']
search_keys = []
post_limit = 0

RedditReader = download_loader('RedditReader')
loader = RedditReader()
documents = loader.load_data(subreddits=subreddits, search_keys=search_keys, post_limit=post_limit)
index = GPTSimpleVectorIndex.from_documents(documents)

def start_query_func(index):
    def query_func(q):
        return index.query(q)
    return query_func

reddit_index_tool = Tool(
    name="Reddit",
    func=lambda q: start_query_func(index),
    description=f"This is Ledger's subreddit where Ledger users from around the world come to discuss about Ledger products and get support to solve technical issues. Useful to gauge user sentiment about a feature or find the answer to very niche technical issues.",
)

# Prepare Zendesk tool
ZendeskReader = download_loader("ZendeskReader")
loader = ZendeskReader(zendesk_subdomain="ledger", locale="en-us")
documents = loader.load_data()

index = GPTSimpleVectorIndex.from_documents(documents)

def generate_query_func(index):
    def query_func(q):
        return index.query(q)
    return query_func

zendesk = Tool(
    name="Help Center",
    func=generate_query_func(index),
    description=f"This is the Ledger Help Center. Use this tool to find the solution to most technical and shipping issues affecting Ledger products. If you find a helpful article, include the url link to the article in your response"
    )
# Prepare toolbox
serpapi_tool = load_tools(["serpapi"])[0]
tools = [serpapi_tool, reddit_index_tool, cal]
tools[0].name = "Google Search"


# Run agent
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

# Define Flask app
app = Flask(__name__, static_folder='static')


# Define authentication function
def authenticate(signature):
    w3 = Web3(Web3.HTTPProvider(os.environ['WEB3_PROVIDER']))
    message = "Access to chat bot"
    message_hash = encode_defunct(text=message)
    signed_message = w3.eth.account.recover_message(message_hash, signature=signature)
    balance = int(contract.functions.balanceOf(signed_message).call())
    if balance > 0:
        token = uuid.uuid4().hex
        response = make_response(redirect('/gpt'))
        response.set_cookie("authToken", token, httponly=True, secure=True, samesite="strict")
        return response
    else:
        return "You don't have the required NFT!"


# Define function to check for authToken cookie
def has_auth_token(request):
    authToken = request.cookies.get("authToken")
    return authToken is not None

# Define Flask endpoints
@app.route("/")
def home():
    return render_template("auth.html")

@app.route("/auth")
def auth():
    signature = request.args.get("signature")
    response = authenticate(signature)
    return response

@app.route("/gpt")
def gpt():
    if has_auth_token(request):
        return render_template("index.html")
    else:
        return redirect("/")

@app.route('/api', methods=['POST'])
def react_description():
    print(request.json)
    # Get user input from request
    user_input = request.json.get('user_input')  
    memory.chat_memory.add_user_message(user_input)
    
    # Run the OpenAI agent on the user input
    output = agent.run(user_input)
    memory.chat_memory.add_ai_message(output)
    response = conversation.predict(input=user_input)

    # Return the output as JSON
    return jsonify({'output': output})


ADDRESS = "0xb022C9c672592c274397557556955eE968052969"
ABI = [{"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"approved","type":"address"},{"indexed":True,"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"operator","type":"address"},{"indexed":False,"internalType":"bool","name":"approved","type":"bool"}],"name":"ApprovalForAll","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":True,"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"approve","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"getApproved","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"string","name":"tokenURI","type":"string"}],"name":"safeMint","outputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"safeTransferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"},{"internalType":"bytes","name":"_data","type":"bytes"}],"name":"safeTransferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"operator","type":"address"},{"internalType":"bool","name":"approved","type":"bool"}],"name":"setApprovalForAll","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenByIndex","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenOfOwnerByIndex","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"tokenURI","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"transferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}]
contract = web3.eth.contract(address=ADDRESS, abi=ABI)

# Start the Flask app
if __name__ == '__main__':
    app.run(port=8000)
