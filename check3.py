import streamlit as st
import requests
import json
from groq import Groq
import re  # Importing regex for email validation

# Initialize Groq client
client = Groq(api_key="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")
MODEL = 'llama3-groq-8b-8192-tool-use-preview' 

# Function to validate email
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Define the booking function
def do_booking(booking_email, phone, ticks):
    url = "https://easeentry-api.vercel.app/api/bookings"
    headers = {"Content-Type": "application/json"}
    
    if not is_valid_email(booking_email):
        return {"error": "Invalid email format."}
    
    try:
        phone = int(phone)
        ticks = int(ticks)
    except ValueError:
        return {"error": "Phone number and tickets must be numerical values."}
    
    data = {
        "booking_email": booking_email,
        "phone": phone,
        "ticks": ticks
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        if response.status_code == 201 and "message" in response.json():
            return {"success": True, "message": "Booking successful"}
        else:
            return {"error": f"Unexpected response: {response.content}"}
    except requests.RequestException as e:
        error_message = f"Request failed: {str(e)}"
        if e.response is not None:
            error_message += f" Response content: {e.response.content}"
        return {"error": error_message}

# Define the function to get ticket information
def get_ticket_info(ticket_id):
    url = f"https://easeentry-api.vercel.app/api/bookings/{int(ticket_id)}"
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()

        if "data" in data and data["data"]:
            ticket_info = data["data"][0]
            return {
                "amount": ticket_info.get("amount"),
                "booking_email": ticket_info.get("booking-email"),
                "booking_id": ticket_info.get("booking-id"),
                "validity": ticket_info.get("validity")
            }
        else:
            return {"error": "No ticket information found."}

    except requests.RequestException as e:
        error_message = f"Request failed: {str(e)}"
        if e.response is not None:
            error_message += f" Response content: {e.response.content}"
        return {"error": error_message}

def get_website_information():
    api_url = 'https://easeentry-api.vercel.app/api/websiteinformation'
    
    try:
        response = requests.get(api_url)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return {'error': f"API returned status code {response.status_code}"}
    
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}

# Set page config
st.set_page_config(page_title="Athena Museum Booking Assistant", page_icon="🏛️", layout="wide")

# Streamlit UI Setup
st.title("🏛️ Athena Museum Booking Assistant")
st.markdown("Welcome to the Athena Museum Booking Assistant. How may I help you today?")

# Initialize conversation history in session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

# System message (hidden from the user)
system_message = {
    "role": "system",
    "content": (
        """
Your name is EaseEntry AI, your task is to assist users in their bookings and the queries about the museum. You have 3 tools: 
1. Booking: Requires user's email, phone number, and number of tickets. If not provided, ask until given. Instruct users to confirm their booking via the provided payment link to receive their Booking ID.
2. Museum Information: Fetches details regarding the museum.
3. Ticket Information: Retrieve information using the user's booking ID.
        """  
    )
}

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capture user input
user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Define available functions
    available_functions = {
        "do_booking": do_booking,
        "get_ticket_info": get_ticket_info,
        "get_website_information": get_website_information
    }

    # Prepare messages for the API call
    api_messages = [system_message] + st.session_state.messages

    # Send user message to the assistant
    with st.spinner("Thinking..."):
        response = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            temperature=0.5,
            tools=[{
                "type": "function",
                "function": {
                    "name": "do_booking",
                    "description": "Make a booking with the provided email, phone, and number of tickets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "booking_email": {
                                "type": "string",
                                "description": "Email address used for booking"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number associated with the booking"
                            },
                            "ticks": {
                                "type": "integer",
                                "description": "Number of tickets to book"
                            }
                        },
                        "required": ["booking_email", "phone", "ticks"],
                    },
                },
            }, {
                "type": "function",
                "function": {
                    "name": "get_ticket_info",
                    "description": "Retrieve information about a booking using the ticket ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticket_id": {
                                "type": "integer",
                                "description": "The ID of the ticket to retrieve information for"
                            }
                        },
                        "required": ["ticket_id"],
                    },
                },
            }, {
                "type": "function",
                "function": {
                    "name": "get_website_information",
                    "description": "Retrieves information regarding the Athena Museum.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    }
                }
            }],
            tool_choice="auto",
            max_tokens=4096
        )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Process tool calls if any
    if tool_calls:
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(**function_args)
            
            api_messages.append(
                {
                    "role": "function",
                    "name": function_name,
                    "content": json.dumps(function_response)
                }
            )
        
        # Final response after tool call
        second_response = client.chat.completions.create(
            model=MODEL,
            messages=api_messages
        )
        assistant_response = second_response.choices[0].message.content
    else:
        # No tool call, just use the assistant response
        assistant_response = response_message.content

    # Append and display assistant response
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    with st.chat_message("assistant"):
        st.markdown(assistant_response)

# Hide Streamlit style
hide_streamlit_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
