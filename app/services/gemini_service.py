from typing import Optional
from app.services.gemini_client import call_gemini

async def suggest_whatsapp_reply(
    history: str, instruction: Optional[str] = None
) -> str:
    system_inst = "You are a polite, helpful real estate assistant replying to a prospective lead over WhatsApp."
    prompt = f"Recent conversation:\n{history}\n\nAdditional instruction: {instruction or 'Draft a professional concise reply'}\n\nSuggested reply:"
    return await call_gemini(prompt, system_instruction=system_inst)

async def extract_lead_from_text(text: str) -> str:
    prompt = f"Extract Name, Phone, and Email in JSON format only from the following text:\n\n{text}"
    system_inst = "You output strictly valid JSON with keys: name, phone, email."
    return await call_gemini(prompt, system_instruction=system_inst)

async def analyze_call_transcript(transcript: str) -> str:
    prompt = f"Analyze the following call transcript. Extract Summary, Customer Intent, Sentiment, and Action Items:\n\n{transcript}"
    system_inst = "You are an expert CRM sales call analyzer."
    return await call_gemini(prompt, system_instruction=system_inst)

async def summarize_call_transcript(transcript: str) -> str:
    prompt = f"Provide a brief executive summary of this call transcript:\n\n{transcript}"
    system_inst = "You summarize client sales phone conversations accurately."
    return await call_gemini(prompt, system_instruction=system_inst)

async def summarize_conversation_history(convo_text: str) -> str:
    prompt = f"Summarize the key points, customer intent, and next action items from this conversation:\n\n{convo_text}"
    system_inst = "You are a CRM conversation summarizer."
    return await call_gemini(prompt, system_instruction=system_inst)
