import os
import json
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

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

async def send_to_telex(client: httpx.Client, message: str) -> dict:
    """Helper function to send messages to Telex with proper error handling"""
    payload = {
        "content": message
    }
    
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
    return response.json()

@app.post("/zendesk-integration")
async def zendesk_integration(request: Request):
    try:
        data = await request.json()
        
        with httpx.Client(timeout=30.0) as client:
            # Handle ticket data
            if "ticket" in data:
                ticket = data["ticket"]
                
                # Format the ticket message
                message = f"""🎫 **New Ticket #{ticket.get('id', 'Unknown')}**

📌 **Subject:** {ticket.get('subject', 'No Subject')}
🔘 **Status:** {ticket.get('status', 'Unknown')}
⚡ **Priority:** {ticket.get('priority', 'Unknown')}
👤 **Requester:** {ticket.get('requester', {}).get('email', 'Unknown')}

💬 **Description:**
{ticket.get('description', 'No description provided')}"""

                # Add latest comment if present
                latest_comment = ticket.get('latest_comment', {})
                if latest_comment and latest_comment.get('body'):
                    message += f"\n\n📝 **Latest Comment:**\n{latest_comment['body']}"

                await send_to_telex(client, message)

            # Handle separate message data
            if "message" in data and data["message"]:
                message = f"💬 **New Comment:**\n{data['message']}"
                await send_to_telex(client, message)

        return JSONResponse(content={"message": "Successfully sent to Telex"}, status_code=200)
    
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Invalid JSON format"}, status_code=400)
    except httpx.HTTPStatusError as e:
        error_message = f"Telex API error: {str(e)}\nResponse: {e.response.text if hasattr(e, 'response') else 'No response text'}"
        print(error_message)
        return JSONResponse(content={"error": error_message}, status_code=e.response.status_code if hasattr(e, 'response') else 500)
    except httpx.RequestError as e:
        error_message = f"Failed to send request to Telex: {str(e)}"
        print(error_message)
        return JSONResponse(content={"error": error_message}, status_code=500)
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(error_message)
        return JSONResponse(content={"error": error_message}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
