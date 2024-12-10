import openai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
import re
import pyperclip
from fpdf import FPDF
import logging
from langdetect import detect, LangDetectException
from openai import OpenAI
import socket

# Configure Logging
logging.basicConfig(
    filename='youtube_summarizer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def extract_video_id(url):
    """
    Extracts the YouTube video ID from various possible YouTube URL formats.
    """
    parsed_url = urlparse(url)
    patterns = [
        r'youtu\.be/(?P<id>[^/?]+)',
        r'youtube\.com/watch\?v=(?P<id>[^&]+)',
        r'youtube\.com/embed/(?P<id>[^/?]+)',
        r'youtube\.com/v/(?P<id>[^/?]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group('id')
            logging.info(f"Extracted video ID: {video_id}")
            return video_id

    # Fallback to 'v' parameter
    query = parse_qs(parsed_url.query)
    video_id = query.get('v', [None])[0]
    logging.info(f"Extracted video ID from 'v' parameter: {video_id}")
    return video_id

def get_transcript(video_id):
    """
    Retrieves the transcript for the given YouTube video ID.
    Attempts Korean first, then English, then any available language.
    """
    logging.info(f"Attempting to fetch transcript for video ID: {video_id}")
    try:
        socket.setdefaulttimeout(15)  # 15 seconds timeout
        
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        logging.info(f"Available transcript languages: {transcript_list._languages}")
        
        # Try languages in order: Korean, English, then any available
        for lang in ['ko', 'en']:
            try:
                transcript = transcript_list.find_transcript([lang])
                logging.info(f"Found {lang} transcript.")
                break
            except NoTranscriptFound:
                continue
        else:
            # If no preferred language found, use any available
            transcript = transcript_list.find_transcript(transcript_list._languages)
            logging.info(f"Found transcript in language: {transcript.language}")

        transcript_data = transcript.fetch()
        full_text = " ".join([entry['text'] for entry in transcript_data])
        logging.info("Transcript fetched successfully.")
        return full_text, transcript.language

    except (TranscriptsDisabled, NoTranscriptFound, Exception) as e:
        error_msg = f"Error fetching transcript: {str(e)}"
        logging.error(error_msg)
        return None, error_msg

def detect_language(text):
    """
    Detects the language of the given text.
    """
    try:
        language = detect(text)
        logging.info(f"Detected language: {language}")
        return language
    except LangDetectException as e:
        logging.error(f"Language detection failed: {e}")
        return 'en'  # Default to English if detection fails

def summarize_text(text, api_key, model="grok-beta", max_tokens=300, language='en'):
    """
    Summarizes the provided text using X.AI's Grok model.
    """
    client = get_client(api_key)

    # Modified prompt to explicitly request non-bold text
    prompt = (
        f"Please provide a concise summary in {language} for the following transcript. "
        f"Output in a Markdown format. When necessary, Format each point with a bullet (•) or dash (-). Though do not use bold text formatting in your response:\n\n{text}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes text and outputs in a markdown format"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.5,
        )

        summary = response.choices[0].message.content.strip()
        logging.info("Summary generated successfully.")

        return {
            "summary": summary,
            "model_used": model,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return None

def save_as_txt(text, file_path):
    """
    Saves the provided text to a TXT file.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(text)
        logging.info(f"Summary saved as TXT: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save summary as TXT: {e}")
        return False

def save_as_pdf(text, file_path):
    """
    Saves the provided text to a PDF file.
    """
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Helvetica", size=12)
        for line in text.split('\n'):
            pdf.multi_cell(0, 10, line)
        pdf.output(file_path)
        logging.info(f"Summary saved as PDF: {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save summary as PDF: {e}")
        return False

def copy_to_clipboard(text):
    """
    Copies the provided text to the system clipboard.
    """
    try:
        pyperclip.copy(text)
        logging.info("Summary copied to clipboard.")
        return True
    except pyperclip.PyperclipException as e:
        logging.error(f"Failed to copy to clipboard: {e}")
        return False

def generate_full_summary(event=None):
    """
    Generates a full summary of the transcript.
    """
    youtube_url = url_entry.get().strip()
    api_key = api_key_entry.get().strip()
    selected_model = model_var.get()
    output_language = output_language_var.get()

    if not youtube_url:
        status_label.config(text="Please enter a YouTube video URL.")
        logging.warning("User did not enter a YouTube video URL.")
        return

    if not api_key:
        status_label.config(text="Please enter your API key.")
        logging.warning("User did not enter an API key.")
        return

    video_id = extract_video_id(youtube_url)
    if not video_id:
        status_label.config(text="Invalid YouTube URL. Please check and try again.")
        logging.error("Invalid YouTube URL provided by user.")
        return

    # Disable the button to prevent multiple clicks
    generate_button.config(state=tk.DISABLED)
    summary_text_area.delete(1.0, tk.END)
    additional_info_area.delete(1.0, tk.END)
    status_label.config(text="Fetching transcript...")

    # Fetch transcript
    transcript, transcript_language = get_transcript(video_id)
    if not transcript:
        status_label.config(text="Failed to retrieve transcript.")
        generate_button.config(state=tk.NORMAL)
        return

    # Detect the dominant language of the transcript
    language = detect_language(transcript)

    # Determine output language
    if output_language == "Transcript Language":
        summary_language = language
    else:
        summary_language = "English"

    status_label.config(text="Generating full summary...")

    # Summarize transcript
    result = summarize_text(transcript, api_key, model=selected_model, language=summary_language)

    if result and "summary" in result:
        summary = result["summary"]
        summary_text_area.insert(tk.END, summary)

        status_label.config(text="Full summary generated successfully.")

        # Enable save and copy buttons
        save_txt_button.config(state=tk.NORMAL)
        save_pdf_button.config(state=tk.NORMAL)
        copy_clipboard_button.config(state=tk.NORMAL)
    else:
        status_label.config(text="Failed to generate full summary.")

    # Re-enable the button
    generate_button.config(state=tk.NORMAL)

def generate_concise_summary(event=None):
    """
    Generates a concise summary of the transcript in 4 sentences.
    """
    youtube_url = url_entry.get().strip()
    api_key = api_key_entry.get().strip()
    selected_model = model_var.get()
    output_language = output_language_var.get()

    if not youtube_url:
        status_label.config(text="Please enter a YouTube video URL.")
        logging.warning("User did not enter a YouTube video URL.")
        return

    if not api_key:
        status_label.config(text="Please enter your API key.")
        logging.warning("User did not enter an API key.")
        return

    video_id = extract_video_id(youtube_url)
    if not video_id:
        status_label.config(text="Invalid YouTube URL. Please check and try again.")
        logging.error("Invalid YouTube URL provided by user.")
        return

    # Disable the button to prevent multiple clicks
    concise_summary_button.config(state=tk.DISABLED)
    summary_text_area.delete(1.0, tk.END)
    additional_info_area.delete(1.0, tk.END)
    status_label.config(text="Fetching transcript...")

    # Fetch transcript
    transcript, transcript_language = get_transcript(video_id)
    if not transcript:
        status_label.config(text="Failed to retrieve transcript.")
        concise_summary_button.config(state=tk.NORMAL)
        return

    # Detect the dominant language of the transcript
    language = detect_language(transcript)

    # Determine output language
    if output_language == "Transcript Language":
        summary_language = language
    else:
        summary_language = "English"

    status_label.config(text="Generating short summary...")

    # Prepare a concise summary prompt with strict sentence limit
    prompt = (
        f"Please provide an extremely concise summary of the following transcript in {summary_language}, "
        f"using maximum of 4 bullet points. Format each point with a bullet (•) or dash (-) followed by a single sentence. Output in markdown format: \n\n{transcript}"
    )

    try:
        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes text and outputs in a markdown format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.5,
        )

        summary = response.choices[0].message['content'].strip()
        logging.info("Short summary generated successfully.")

        # Extract usage details
        usage = response['usage']
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        # Determine the model used
        model_used = response.get('model', selected_model)

        # Ensure summary has at most 4 sentences
        sentences = re.split(r'(?<=[.!?]) +', summary)
        if len(sentences) > 4:
            sentences = sentences[:4]
            summary = ' '.join(sentences)
            logging.warning("Short summary exceeded 4 sentences. Truncated to 4.")

        summary_text_area.insert(tk.END, summary)

        status_label.config(text="Short summary generated successfully.")

        # Enable save and copy buttons
        save_txt_button.config(state=tk.NORMAL)
        save_pdf_button.config(state=tk.NORMAL)
        copy_clipboard_button.config(state=tk.NORMAL)

    except openai.error.OpenAIError as e:
        logging.error(f"OpenAIError during short summary: {e}")
        status_label.config(text=f"Failed to generate short summary: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during short summary: {e}")
        status_label.config(text=f"Failed to generate short summary: {e}")

    # Re-enable the button
    concise_summary_button.config(state=tk.NORMAL)

def generate_custom_prompt(event=None):
    """
    Generates a summary based on a user-defined custom prompt.
    """
    custom_prompt = custom_prompt_entry.get("1.0", tk.END).strip()
    youtube_url = url_entry.get().strip()
    api_key = api_key_entry.get().strip()
    selected_model = model_var.get()
    output_language = output_language_var.get()

    if not youtube_url:
        status_label.config(text="Please enter a YouTube video URL.")
        logging.warning("User did not enter a YouTube video URL.")
        return

    if not api_key:
        status_label.config(text="Please enter your API key.")
        logging.warning("User did not enter an API key.")
        return

    if not custom_prompt:
        status_label.config(text="Please enter a custom prompt.")
        logging.warning("User did not enter a custom prompt.")
        return

    video_id = extract_video_id(youtube_url)
    if not video_id:
        status_label.config(text="Invalid YouTube URL. Please check and try again.")
        logging.error("Invalid YouTube URL provided by user.")
        return

    # Disable the button to prevent multiple clicks
    prompt_button.config(state=tk.DISABLED)
    summary_text_area.delete(1.0, tk.END)
    additional_info_area.delete(1.0, tk.END)
    status_label.config(text="Fetching transcript...")

    # Fetch transcript
    transcript, transcript_language = get_transcript(video_id)
    if not transcript:
        status_label.config(text="Failed to retrieve transcript.")
        prompt_button.config(state=tk.NORMAL)
        return

    # Detect the dominant language of the transcript
    language = detect_language(transcript)

    # Determine output language
    if output_language == "Transcript Language":
        summary_language = language
    else:
        summary_language = "English"

    status_label.config(text="Generating custom summary...")

    # Prepare the custom prompt with language specification
    prompt = f"The output should be in markdown format and when necessary, Format each point with a bullet (•) or dash (-). Respond to this prompt "{custom_prompt}" in {summary_language}. For the following transcript:\n\n{transcript}"

    try:
        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes text and outputs in a markdown format"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.5,
        )

        summary = response.choices[0].message['content'].strip()
        logging.info("Custom summary generated successfully.")

        # Extract usage details
        usage = response['usage']
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)

        # Determine the model used
        model_used = response.get('model', selected_model)

        # Insert the summary without any markdown formatting
        summary_text_area.insert(tk.END, summary)

        status_label.config(text="Custom summary generated successfully.")

        # Enable save and copy buttons
        save_txt_button.config(state=tk.NORMAL)
        save_pdf_button.config(state=tk.NORMAL)
        copy_clipboard_button.config(state=tk.NORMAL)

    except openai.error.OpenAIError as e:
        logging.error(f"OpenAIError during custom summary: {e}")
        status_label.config(text=f"Failed to generate custom summary: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during custom summary: {e}")
        status_label.config(text=f"Failed to generate custom summary: {e}")

    # Re-enable the button
    prompt_button.config(state=tk.NORMAL)

def toggle_prompt_entry(event=None):
    """
    Toggles the visibility of the custom prompt entry field.
    """
    if custom_prompt_frame.winfo_viewable():
        custom_prompt_frame.grid_remove()
    else:
        custom_prompt_frame.grid()

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

