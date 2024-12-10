from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import sys
from openai import OpenAI
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummaryRequest(BaseModel):
    youtube_url: str
    api_key: str
    output_language: str = "English"
    summary_type: str
    custom_prompt: Optional[str] = ""

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_transcript(video_id):
    """Get transcript from YouTube video"""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript_list]), None
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

def detect_language(text):
    """Detect language of text"""
    from langdetect import detect
    try:
        return detect(text)
    except:
        return "en"


def get_client(api_key):
    """
    Creates and returns an OpenAI client instance with the provided API key.
    """
    try:


        XAI_API_KEY = api_key
        client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        logging.info("XAI client created successfully")


        return client
    except Exception as e:
        logging.error(f"Error creating XAI client: {e}")
        raise

def process_summary(youtube_url, api_key, selected_model, output_language, summary_type, custom_prompt=""):
    """
    Unified function to handle all types of summaries
    """
    if not youtube_url or not api_key:
        return "Please provide both YouTube URL and API key.", "No summary generated."

    if not api_key.startswith('xai-'):
        return "Invalid API key format. X.AI API keys should start with 'xai-'", "No summary generated."

    try:
        client = get_client(api_key)
        
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return "Invalid YouTube URL. Please check and try again.", "No summary generated."

        # Fetch transcript
        transcript, error_or_language = get_transcript(video_id)
        if not transcript:
            return f"Failed to retrieve transcript: {error_or_language}", "No summary generated."

        # Detect language
        language = detect_language(transcript)
        summary_language = "English" if output_language == "English" else language

        # Prepare prompt based on summary type
        if summary_type == "short":
            prompt = (
                f"Please provide a very concise summary of the following transcript in {summary_language}, "
                f"using a maximum of 4 sentences in bullet points.\n\n{transcript}"
            )
        elif summary_type == "custom":
            if not custom_prompt:
                return "Please provide a custom prompt.", "No summary generated."
            prompt = f"Please {custom_prompt} in {summary_language} for the following transcript without using any markdown formatting:\n\n{transcript}"
        else:  # full summary
            prompt = f"Please provide a comprehensive summary in {summary_language} for the following transcript without using any markdown formatting:\n\n{transcript}"

        try:
            response = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.5,
            )

            summary = response.choices[0].message.content.strip()
            
            # Extract usage details
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Prepare additional info
            additional_info = (
                f"Model: grok-beta\n"
                f"Tokens Used:\n"
                f"  - Prompt Tokens: {prompt_tokens}\n"
                f"  - Completion Tokens: {completion_tokens}\n"
                f"  - Total Tokens: {total_tokens}\n"
            )

            return summary, additional_info

        except Exception as e:
            logging.error(f"API Error: {str(e)}")
            return f"Error calling X.AI API: {str(e)}", "Error occurred"

    except Exception as e:
        logging.error(f"Error in process_summary: {e}")
        return f"Error: {str(e)}", "Error occurred"

@app.post("/api/summarize")
async def summarize(request: SummaryRequest):
    try:
        summary, additional_info = process_summary(
            request.youtube_url,
            request.api_key,
            "grok-beta",
            request.output_language,
            request.summary_type,
            request.custom_prompt
        )
        return {
            "success": True,
            "summary": summary,
            "additional_info": additional_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}