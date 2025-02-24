import os
import logging
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('zendesk_integration.log')
    ]
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

TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    logger.error("TELEX_CHANNEL_ID is not set in environment variables!")
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request):
    try:
        # Log incoming request
        body = await request.body()
        logger.info("Incoming request data: %s", body.decode())
        
        # Parse JSON data
        data = await request.json()
        
        # Validate ticket data
        if not isinstance(data, dict) or "ticket" not in data:
            logger.warning("Invalid request format - missing ticket data")
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Invalid request format. This endpoint only accepts Zendesk ticket webhooks.",
                    "expected_format": {
                        "ticket": {
                            "id": "string",
                            "subject": "string",
                            "description": "string",
                            "requester": {
                                "email": "string",
                                "name": "string"
                            },
                            "status": "string"
                        }
                    }
                },
                status_code=400
            )
            
        ticket = data["ticket"]
        
        # Extract ticket details
        ticket_id = str(ticket.get("id", "Unknown"))
        subject = ticket.get("subject", "No Subject")
        message = ticket.get("description", "No message provided")
        requester = ticket.get("requester", {})
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")
        
        # Payload for Telex
        telex_payload = {
            "event_name": "Zendesk New Ticket",
            "username": "ZendeskBot",
            "status": "success",
            "message": (
                f"\U0001F3AB **Ticket:** #{ticket_id}\n"
                f"\U0001F4CC **Subject:** {subject}\n"
                f"\U0001F518 **Status:** {status}\n"
                f"⚡ **Priority:** {priority}\n"
                f"\U0001F464 **Requester:** {requester_email}\n"
                f"\U0001F4AC **Message:** {message}"
            )
        }
        
        logger.info(f"Sending payload to Telex: {json.dumps(telex_payload, indent=2)}")
        
        # Send to Telex
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TELEX_WEBHOOK_URL,
                json=telex_payload,
                headers={"Content-Type": "application/json"},
                follow_redirects=True
            )
            
            if response.status_code >= 400:
                logger.error(f"Telex error response: {response.status_code}, {response.text}")
                return JSONResponse(
                    content={"error": "Failed to send to Telex"},
                    status_code=response.status_code
                )
            
            logger.info(f"Successfully processed ticket #{ticket_id}")
            return JSONResponse(
                content={"message": "Successfully sent to Telex"},
                status_code=200
            )
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )
