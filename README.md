# Telex-Zendesk Integration Webhook

This is a **FastAPI webhook** that listens for **Zendesk ticket updates** and forwards the details to a **Telex.im** channel.

## 🚀 Features
- ✅ Receives **Zendesk webhook requests**.
- ✅ Extracts ticket details (subject, status, priority, message, requester).
- ✅ Forwards the ticket update **to Telex.im**.
- ✅ Uses **environment variables** for security.
- ✅ Implements **async HTTP requests with `httpx`**.
- ✅ **Deployed on Koyeb** for scalability.

---

## 🛠️ Installation

### 1️⃣ Clone the repository
```sh
git clone https://github.com/telexintegrations/zendesk-integration.git
cd zendesk-integration
```

### 2️⃣ Create a virtual environment
```sh
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3️⃣ Install dependencies
```sh
pip install -r requirements.txt
```

### 4️⃣ Set up environment variables  
Create a `.env` file in the root directory:
```ini
TELEX_CHANNEL_ID=your_telex_channel_id
ZENDESK_WEBHOOK_SECRET=your_zendesk_secret #if you want to validate ZenDesk requests
```

---

## ▶️ Running the Webhook
Start the FastAPI server locally:
```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌍 Deploying on Koyeb
1. **Push your code to GitHub**:  
   ```sh
   git push origin main
   ```
2. **Go to [Koyeb](https://www.koyeb.com/) and create a new service.**  
3. **Connect your GitHub repository**:  
   - Select `https://github.com/telexintegrations/zendesk-integration`
   - Choose `main.py` as the entry point.  
   - Set up environment variables (`TELEX_CHANNEL_ID`, `ZENDESK_WEBHOOK_SECRET`).  
4. **Deploy and monitor logs**:  
   ```sh
   koyeb logs -a your-app-name
   ```

---

## 🔄 Testing the Webhook
Use **Postman** or **cURL** to send a test request:
```sh
curl -X POST "https://ratty-goldarina-kenward-15941202.koyeb.app/zendesk-integration" \
     -H "Content-Type: application/json" \
     -d '{
           "ticket": {
               "id": 12345,
               "subject": "Delayed Delivery",
               "requester": {"email": "customer@example.com"},
               "status": "open",
               "priority": "high",
               "description": "My order is late.",
               "latest_comment": {"body": "Still waiting for an update."}
           }
       }'
```

Expected Response:
```json
{"message": "Sent to Telex"}
```

---

## ✅ Running Tests
Make sure **pytest** is installed:
Not implemented yet


---


### 📧 Contact  
📩 **Author**: [Kenward-dev](https://github.com/Kenward-dev)  
🏢 **GitHub Organization**: [Telex Integrations](https://github.com/telexintegrations/zendesk-integration)
```
