import openai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
import re
import pyperclip
from fpdf import FPDF
import logging
from langdetect import detect, LangDetectException
from openai import OpenAI

# Configure Logging
logging.basicConfig(
    filename='youtube_summarizer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define model pricing based on OpenAI's latest pricing (update as needed)
# Prices are converted from per 1M tokens to per 1k tokens by dividing by 1000
model_prices = {
    "chatgpt-4o-latest": {"prompt": 5.00 / 1000, "completion": 15.00 / 1000},
    "gpt-4-turbo": {"prompt": 10.00 / 1000, "completion": 30.00 / 1000},
    "gpt-4-turbo-2024-04-09": {"prompt": 10.00 / 1000, "completion": 30.00 / 1000},
    "gpt-4": {"prompt": 30.00 / 1000, "completion": 60.00 / 1000},
    "gpt-4-32k": {"prompt": 60.00 / 1000, "completion": 120.00 / 1000},
    "gpt-4-0125-preview": {"prompt": 10.00 / 1000, "completion": 30.00 / 1000},
    "gpt-4-1106-preview": {"prompt": 10.00 / 1000, "completion": 30.00 / 1000},
    "gpt-4-vision-preview": {"prompt": 10.00 / 1000, "completion": 30.00 / 1000},
    "gpt-3.5-turbo-0125": {"prompt": 0.50 / 1000, "completion": 1.50 / 1000},
    "gpt-3.5-turbo-instruct": {"prompt": 1.50 / 1000, "completion": 2.00 / 1000},
    "gpt-3.5-turbo-1106": {"prompt": 1.00 / 1000, "completion": 2.00 / 1000},
    "gpt-3.5-turbo-0613": {"prompt": 1.50 / 1000, "completion": 2.00 / 1000},
    "gpt-3.5-turbo-16k-0613": {"prompt": 3.00 / 1000, "completion": 4.00 / 1000},
    "gpt-3.5-turbo-0301": {"prompt": 1.50 / 1000, "completion": 2.00 / 1000},
    "davinci-002": {"prompt": 2.00 / 1000, "completion": 2.00 / 1000},
    "babbage-002": {"prompt": 0.40 / 1000, "completion": 0.40 / 1000},
    # Add other models and their prices as needed
}

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
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Attempt Korean
        try:
            transcript = transcript_list.find_transcript(['ko'])
            logging.info("Found Korean transcript.")
        except NoTranscriptFound:
            logging.info("Korean transcript not found. Trying English.")
            # Attempt English
            try:
                transcript = transcript_list.find_transcript(['en'])
                logging.info("Found English transcript.")
            except NoTranscriptFound:
                # Fallback to any available language
                transcript = transcript_list.find_transcript(transcript_list._languages)
                logging.info(f"Found transcript in language: {transcript.language}")

        transcript_data = transcript.fetch()
        full_text = " ".join([entry['text'] for entry in transcript_data])
        logging.info("Transcript fetched successfully.")
        return full_text, transcript.language

    except TranscriptsDisabled:
        error_msg = "Transcripts are disabled for this video by the content creator."
        logging.error(error_msg)
        return None, error_msg
    except NoTranscriptFound:
        error_msg = "No transcript is available for this video in any language."
        logging.error(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Error fetching transcript: {str(e)}. This might be due to network issues or API restrictions."
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
    Summarizes the provided text using X.AI's Grok model in a single API request.
    Retrieves tokens used and generates summary in the specified language.
    """
    client = get_client(api_key)

    # Prepare the prompt with language specification
    prompt = f"Please provide a concise summary in {language} for the following transcript without using any markdown formatting:\n\n{text}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.5,
        )

        summary = response.choices[0].message.content.strip()
        logging.info("Summary generated successfully.")

        # Extract usage details
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        return {
            "summary": summary,
            "model_used": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "expected_cost": None  # Grok pricing not public
        }

    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return None

def save_as_txt(text):
    """
    Saves the provided text to a TXT file.
    """
    try:
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(text)
            logging.info(f"Summary saved as TXT: {file_path}")
            status_label.config(text=f"Summary saved as TXT: {file_path}")
    except Exception as e:
        logging.error(f"Failed to save summary as TXT: {e}")
        status_label.config(text=f"Failed to save summary as TXT: {e}")

def save_as_pdf(text):
    """
    Saves the provided text to a PDF file.
    """
    try:
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                 filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if file_path:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", size=12)  # Changed to sans-serif
            for line in text.split('\n'):
                pdf.multi_cell(0, 10, line)
            pdf.output(file_path)
            logging.info(f"Summary saved as PDF: {file_path}")
            status_label.config(text=f"Summary saved as PDF: {file_path}")
    except Exception as e:
        logging.error(f"Failed to save summary as PDF: {e}")
        status_label.config(text=f"Failed to save summary as PDF: {e}")

def copy_to_clipboard(text):
    """
    Copies the provided text to the system clipboard.
    """
    try:
        pyperclip.copy(text)
        logging.info("Summary copied to clipboard.")
        status_label.config(text="Summary copied to clipboard.")
    except pyperclip.PyperclipException as e:
        logging.error(f"Failed to copy to clipboard: {e}")
        status_label.config(text=f"Failed to copy to clipboard: {e}")

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

        additional_info = (
            f"GPT Model Version Used: {result['model_used']}\n"
            f"Tokens Used:\n"
            f"  - Prompt Tokens: {result['prompt_tokens']}\n"
            f"  - Completion Tokens: {result['completion_tokens']}\n"
            f"  - Total Tokens: {result['total_tokens']}\n"
        )
        if result["expected_cost"] is not None:
            additional_info += f"Expected Cost: ${result['expected_cost']} USD"
        else:
            additional_info += "Expected Cost: Model pricing not available."

        additional_info_area.insert(tk.END, additional_info)
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
        f"Please provide a very concise summary of the following transcript in {summary_language}, "
        f"using a maximum of 4 sentences. Do not use any markdown formatting.\n\n{transcript}"
    )

    try:
        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes text."},
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

        # Calculate expected cost
        if model_used in model_prices:
            prompt_cost = (prompt_tokens / 1000) * model_prices[model_used]['prompt']
            completion_cost = (completion_tokens / 1000) * model_prices[model_used]['completion']
            total_cost = prompt_cost + completion_cost
            total_cost = round(total_cost, 6)
            logging.info(f"Model Used: {model_used}, Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Total Tokens: {total_tokens}, Expected Cost: ${total_cost} USD")
        else:
            prompt_cost = completion_cost = total_cost = None
            logging.warning(f"Model pricing not found for model: {model_used}")

        # Ensure summary has at most 4 sentences
        sentences = re.split(r'(?<=[.!?]) +', summary)
        if len(sentences) > 4:
            sentences = sentences[:4]
            summary = ' '.join(sentences)
            logging.warning("Short summary exceeded 4 sentences. Truncated to 4.")

        summary_text_area.insert(tk.END, summary)

        additional_info = (
            f"GPT Model Version Used: {model_used}\n"
            f"Tokens Used:\n"
            f"  - Prompt Tokens: {prompt_tokens}\n"
            f"  - Completion Tokens: {completion_tokens}\n"
            f"  - Total Tokens: {total_tokens}\n"
        )
        if total_cost is not None:
            additional_info += f"Expected Cost: ${total_cost} USD"
        else:
            additional_info += "Expected Cost: Model pricing not available."

        additional_info_area.insert(tk.END, additional_info)
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
    prompt = f"Please {custom_prompt} in {summary_language} for the following transcript without using any markdown formatting:\n\n{transcript}"

    try:
        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are an assistant that summarizes text."},
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

        # Calculate expected cost
        if model_used in model_prices:
            prompt_cost = (prompt_tokens / 1000) * model_prices[model_used]['prompt']
            completion_cost = (completion_tokens / 1000) * model_prices[model_used]['completion']
            total_cost = prompt_cost + completion_cost
            total_cost = round(total_cost, 6)
            logging.info(f"Model Used: {model_used}, Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Total Tokens: {total_tokens}, Expected Cost: ${total_cost} USD")
        else:
            prompt_cost = completion_cost = total_cost = None
            logging.warning(f"Model pricing not found for model: {model_used}")

        # Insert the summary without any markdown formatting
        summary_text_area.insert(tk.END, summary)

        additional_info = (
            f"GPT Model Version Used: {model_used}\n"
            f"Tokens Used:\n"
            f"  - Prompt Tokens: {prompt_tokens}\n"
            f"  - Completion Tokens: {completion_tokens}\n"
            f"  - Total Tokens: {total_tokens}\n"
        )
        if total_cost is not None:
            additional_info += f"Expected Cost: ${total_cost} USD"
        else:
            additional_info += "Expected Cost: Model pricing not available."

        additional_info_area.insert(tk.END, additional_info)
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

