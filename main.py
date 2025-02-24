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

# Retrieve Telex webhook details
TELEX_CHANNEL_ID = os.getenv("TELEX_CHANNEL_ID")
if not TELEX_CHANNEL_ID:
    logger.error("TELEX_CHANNEL_ID is not set in environment variables!")
    raise ValueError("TELEX_CHANNEL_ID is not set in environment variables!")

TELEX_WEBHOOK_URL = f"https://ping.telex.im/v1/webhooks/{TELEX_CHANNEL_ID}"

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request) -> JSONResponse:
    try:
        # Log incoming request data
        body = await request.body()
        logger.info("Incoming request data: %s", body.decode())
        
        # Parse JSON data
        data = await request.json()
        ticket = data.get("ticket", {})
        
        # Validate required fields
        if not ticket:
            logger.error("Missing 'ticket' data in request")
            return JSONResponse(content={"error": "Missing 'ticket' data in request."}, status_code=400)
            
        # Extract ticket details
        ticket_id = str(ticket.get("id", "Unknown"))
        requester = ticket.get("requester", {})
        subject = ticket.get("subject", "No Subject")
        requester_email = requester.get("email", "Unknown")
        status = ticket.get("status", "Unknown")
        priority = ticket.get("priority", "Unknown")
        message = ticket.get("latest_comment", {}).get("body") or ticket.get("description") or "No message provided"
        
        logger.info(f"Processing ticket #{ticket_id} from {requester_email}")
        
        # Payload sent to Telex
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
        
        # Log the payload being sent to Telex
        logger.info(f"Sending payload to Telex: {json.dumps(telex_payload, indent=2)}")
        
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
            
            # Log the complete response from Telex
            logger.info(f"Telex response status: {response.status_code}")
            logger.info(f"Telex response headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                logger.info(f"Telex response body: {json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                logger.info(f"Telex response body (raw): {response.text}")
            
            # Check for error responses
            if response.status_code >= 400:
                logger.error(f"Telex error response: Status {response.status_code}, Body: {response.text}")
                return JSONResponse(
                    content={
                        "error": "Error from Telex",
                        "status_code": response.status_code,
                        "response": response.text
                    }, 
                    status_code=response.status_code
                )
            
            response.raise_for_status()
            logger.info(f"Successfully sent ticket #{ticket_id} to Telex")
            return JSONResponse(content={"message": "Sent to Telex"}, status_code=200)
            
    except httpx.RequestError as e:
        logger.error(f"Failed to send request to Telex: {str(e)}")
        return JSONResponse(content={"error": "Failed to send request to Telex"}, status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Zendesk-Telex Integration service")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Zendesk-Telex Integration service")
