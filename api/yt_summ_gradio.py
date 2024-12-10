from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import sys
from openai import OpenAI
from typing import Optional
import json
from datetime import datetime
import os

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
    allow_origins=[
        "http://localhost:3000",
        "https://yt-summ-gradio.vercel.app",
        "https://yt-summ-gradio-git-main.vercel.app",
        "https://yt-summ-gradio-*.vercel.app"
    ],
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

class FeatureRequest(BaseModel):
    request_text: str
    requester_name: str
    timestamp: Optional[str] = None

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
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, NoTranscriptAvailable
    
    try:
        # First try direct transcript retrieval for auto-generated transcripts
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
            return " ".join([t['text'] for t in transcript_list]), None
        except:
            # If direct retrieval fails, try the list_transcripts approach
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Get all available languages
            available_languages = []
            for transcript in transcript_list:
                available_languages.append(transcript.language_code)
            
            if not available_languages:
                return None, "No transcripts available for this video"
            
            # Try to get any available transcript
            try:
                transcript = transcript_list.find_transcript(available_languages)
                transcript_parts = transcript.fetch()
                return " ".join([t['text'] for t in transcript_parts]), None
            except NoTranscriptAvailable:
                return None, f"No transcript available. Available languages: {', '.join(available_languages)}"
            
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        return None, f"Could not retrieve transcript: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error while retrieving transcript: {str(e)}"

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

        # Language mapping for better prompting
        language_names = {
            'zh': 'Mandarin Chinese',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'ar': 'Standard Arabic',
            'bn': 'Bengali',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ur': 'Urdu',
            'id': 'Indonesian',
            'de': 'German',
            'ja': 'Japanese',
            'sw': 'Swahili',
            'mr': 'Marathi',
            'te': 'Telugu',
            'tr': 'Turkish',
            'ta': 'Tamil',
            'vi': 'Vietnamese',
            'ko': 'Korean',
            'it': 'Italian',
            'pa': 'Punjabi',
            'gu': 'Gujarati',
            'fa': 'Persian',
            'th': 'Thai',
            'pl': 'Polish',
            'uk': 'Ukrainian',
            'ms': 'Malay',
            'kn': 'Kannada',
            'ha': 'Hausa'
        }

        # Get the full language name
        target_language = language_names.get(output_language, output_language)
        if output_language == 'english':
            target_language = 'English'
        elif output_language == 'korean':
            target_language = 'Korean'

        # Prepare system message
        system_message = (
            f"You are an assistant that summarizes text. "
            f"Always provide your response in {target_language}. "
            f"Make sure the summary sounds natural and fluent in {target_language}."
        )

        # Prepare prompt based on summary type
        if summary_type == "short":
            prompt = (
                f"Please provide a very concise summary of the following transcript, "
                f"using a maximum of 4 sentences in bullet points. "
                f"Provide the summary in {target_language}:\n\n{transcript}"
            )
        elif summary_type == "custom":
            if not custom_prompt:
                return "Please provide a custom prompt.", "No summary generated."
            prompt = (
                f"{custom_prompt}\n\n"
                f"Provide the response in {target_language}.\n\n"
                f"Transcript:\n{transcript}"
            )
        else:  # full summary
            prompt = (
                f"Please provide a comprehensive summary of the following transcript. "
                f"Provide the summary in {target_language}:\n\n{transcript}"
            )

        try:
            response = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": system_message},
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
            model_name = response.model  # Get the actual model name from response

            # Prepare additional info with proper hierarchical structure
            additional_info = (
                f"Model Used: {model_name}\n\n"  # Add extra newline after model
                f"Tokens Used:\n\n"
                f"  • Prompt Tokens: {prompt_tokens}\n\n"
                f"  • Completion Tokens: {completion_tokens}\n\n"
                f"  • Total Tokens: {total_tokens}"
            )

            return summary, additional_info

        except Exception as e:
            logging.error(f"API Error: {str(e)}")
            return f"Error calling X.AI API: {str(e)}", "Error occurred"

    except Exception as e:
        logging.error(f"Error in process_summary: {e}")
        return f"Error: {str(e)}", "Error occurred"

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def save_feature_request(request: FeatureRequest):
    """Save feature request to a JSON file"""
    file_path = os.path.join(DATA_DIR, "feature_requests.json")
    
    # Create empty list if file doesn't exist
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump([], f)
    
    # Read existing requests
    with open(file_path, 'r') as f:
        requests = json.load(f)
    
    # Add new request with timestamp
    request_dict = {
        "request_text": request.request_text,
        "requester_name": request.requester_name,
        "timestamp": datetime.now().isoformat()
    }
    requests.append(request_dict)
    
    # Save updated requests
    with open(file_path, 'w') as f:
        json.dump(requests, f, indent=2)

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

@app.post("/api/feature-request")
async def add_feature_request(request: FeatureRequest):
    try:
        save_feature_request(request)
        return {"success": True, "message": "Feature request saved successfully"}
    except Exception as e:
        logging.error(f"Error saving feature request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feature-requests")
async def get_feature_requests():
    try:
        file_path = os.path.join(DATA_DIR, "feature_requests.json")
        if not os.path.exists(file_path):
            return {"requests": []}
        
        with open(file_path, 'r') as f:
            requests = json.load(f)
        return {"requests": requests}
    except Exception as e:
        logging.error(f"Error reading feature requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}