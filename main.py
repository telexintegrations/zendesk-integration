import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx
import logging
import json

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],  
    allow_headers=["*"],
)

# Retrieve Telex webhook details
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        # Log request headers
        headers = dict(request.headers)
        logger.info(f"Received request headers: {json.dumps(headers, indent=2)}")
        
        # Parse JSON data
        data = await request.json()
        logger.info(f"Received raw request data: {json.dumps(data, indent=2)}")
        
        # Check if this is a settings request
        if "settings" in data:
            logger.info("Received settings configuration request")
            logger.info(f"Settings data: {json.dumps(data['settings'], indent=2)}")
            return JSONResponse(content={"message": "Settings received"}, status_code=200)
        
        ticket = data.get("ticket", {})
        if not ticket:
            logger.error("Missing ticket data in request")
            return JSONResponse(content={"error": "Missing 'ticket' data in request."}, status_code=400)

        # Log ticket details
        logger.info(f"Processing ticket: {json.dumps(ticket, indent=2)}")
        
        # Extract ticket details
        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")
        message = ticket.get("latest_comment", {}).get("body") or ticket.get("description") or "No message provided"

        # payload sent to Telex
        telex_payload = {
            "event_name": "Zendesk New Ticket",
            "username": "ZendeskBot",
            "status": "success",
            "message": (
                f"\U0001F3AB Ticket #{ticket_id}\n"
                f"\U0001F4CC Subject: {subject}\n"
                f"\U0001F518 Status: {status}\n"
                f"⚡ Priority: {priority}\n"
                f"\U0001F464 Requester: {requester_email}\n"
                f"\U0001F4AC Message: {message}"
            )
        }
        
        logger.info(f"Sending payload to Telex: {json.dumps(telex_payload, indent=2)}")
        
        # Log Telex webhook URL being used
        logger.info(f"Using Telex webhook URL: {TELEX_WEBHOOK_URL}")
        
        # Send to Telex channel
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=telex_payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                follow_redirects=True
            )
            # Log response details
            logger.info(f"Telex response status: {response.status_code}")
            logger.info(f"Telex response headers: {dict(response.headers)}")
            logger.info(f"Telex response body: {response.text}")
            
            response.raise_for_status()
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)
            
    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        logger.error(f"Request error details: {e.__dict__}")
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(f"Exception details: {e.__dict__}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
