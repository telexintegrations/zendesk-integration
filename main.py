import os
import json
import httpx
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Fetch Telex Channel ID from environment variables
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

def send_to_telex(payload: dict):
    """Helper function to send messages to Telex with proper error handling"""
    try:
        with httpx.Client(timeout=30.0) as client:
            logger.info(f"Sending payload to Telex: {payload}")
            response = client.post(
                TELEX_WEBHOOK_URL,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                follow_redirects=True
            )
            response.raise_for_status()
            logger.info(f"Successfully sent to Telex. Response: {response.json()}")
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Telex API error: {e.response.text if hasattr(e, 'response') else 'No response text'}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request):
    try:
        data = await request.json()
        logger.info(f"Received data: {data}")
        
        # Handle ticket data
        if "ticket" in data:
            ticket = data["ticket"]
            ticket_payload = {
                "event_name": "Zendesk New Ticket",
                "username": "ZendeskBot",
                "status": "success",
                "message": (
                    f"\U0001F3AB **Ticket:** #{ticket.get('id', 'Unknown')}\n"
                    f"\U0001F4CC **Subject:** {ticket.get('subject', 'No Subject')}\n"
                    f"\U0001F518 **Status:** {ticket.get('status', 'Unknown')}\n"
                    f"⚡ **Priority:** {ticket.get('priority', 'Unknown')}\n"
                    f"\U0001F464 **Requester:** {ticket.get('requester', {}).get('email', 'Unknown')}\n"
                    f"\U0001F4AC **Message:** {ticket.get('description', 'No description provided')}"
                )
            }
            send_to_telex(ticket_payload)
        
        # Handle separate message data
        if "message" in data and data["message"]:
            comment_payload = {
                "event_name": "Zendesk New Comment",
                "username": "ZendeskBot",
                "status": "success",
                "message": (
                    f"\U0001F4AC **New Comment:**\n"
                    f"{data['message']}"
                )
            }
            send_to_telex(comment_payload)
        
        return JSONResponse(content={"message": "Successfully sent to Telex"}, status_code=200)
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON format received")
        return JSONResponse(content={"error": "Invalid JSON format"}, status_code=400)
    except httpx.HTTPStatusError as e:
        error_message = f"Telex API error: {str(e)}"
        logger.error(error_message)
        return JSONResponse(content={"error": error_message}, status_code=e.response.status_code if hasattr(e, 'response') else 500)
    except httpx.RequestError as e:
        error_message = f"Failed to send request to Telex: {str(e)}"
        logger.error(error_message)
        return JSONResponse(content={"error": error_message}, status_code=500)
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        return JSONResponse(content={"error": error_message}, status_code=500)
