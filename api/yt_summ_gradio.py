import gradio as gr
import logging
import sys
from openai import OpenAI

# Configure logging to output to stdout only (no file logging in serverless)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

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

def create_gradio_interface():
    """
    Creates the Gradio interface for the YouTube Transcript Summarizer
    """
    with gr.Blocks(title="YouTube Transcript Summarizer") as demo:
        gr.Markdown("# YouTube Transcript Summarizer")
        
        with gr.Row():
            youtube_url = gr.Textbox(
                label="YouTube Video URL",
                placeholder="Enter YouTube video URL here..."
            )
            api_key = gr.Textbox(
                label="API Key",
                placeholder="Enter your X.AI API key here...",
                type="password"
            )

        with gr.Row():
            model_name = gr.Textbox(
                value="grok-beta",
                label="Model Name",
                interactive=False
            )
            language_dropdown = gr.Dropdown(
                choices=["English", "Original Language"],
                value="English",
                label="Output Language"
            )

        with gr.Row():
            custom_prompt = gr.Textbox(
                label="Custom Prompt (Optional)",
                placeholder="Enter your custom prompt here...",
                lines=3,
                visible=False
            )

        with gr.Row():
            submit_btn = gr.Button("Submit Prompt", visible=False)

        with gr.Row():
            full_summary_btn = gr.Button("Full Summary")
            short_summary_btn = gr.Button("Short Summary")
            custom_prompt_btn = gr.Button("Custom Prompt")

        with gr.Row():
            summary_output = gr.Textbox(
                label="Summary",
                lines=10,
                show_copy_button=True
            )
        
        with gr.Row():
            additional_info = gr.Textbox(
                label="Additional Information",
                lines=6
            )

        def process_and_show_buttons(*args, **kwargs):
            summary, info = process_summary(*args, **kwargs)
            return [summary, info]

        submit_btn.click(
            fn=lambda url, key, model, lang, prompt: process_and_show_buttons(
                url, key, model, lang, "custom", prompt
            ),
            inputs=[youtube_url, api_key, model_name, language_dropdown, custom_prompt],
            outputs=[summary_output, additional_info]
        )

        custom_prompt_btn.click(
            fn=lambda: (
                gr.update(visible=True),
                gr.update(visible=True)
            ),
            inputs=[],
            outputs=[custom_prompt, submit_btn]
        )

        full_summary_btn.click(
            fn=lambda url, key, model, lang: process_and_show_buttons(
                url, key, model, lang, "full", ""
            ),
            inputs=[youtube_url, api_key, model_name, language_dropdown],
            outputs=[summary_output, additional_info]
        )

        short_summary_btn.click(
            fn=lambda url, key, model, lang: process_and_show_buttons(
                url, key, model, lang, "short", ""
            ),
            inputs=[youtube_url, api_key, model_name, language_dropdown],
            outputs=[summary_output, additional_info]
        )

        return demo

# Create the Gradio interface
demo = create_gradio_interface()
demo.queue(max_size=10)

# For Vercel deployment
app = demo.app

if __name__ == "__main__":
    demo.launch()