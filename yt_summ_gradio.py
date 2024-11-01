import gradio as gr
import openai
import logging
import pyperclip
import json

# Load environment variables and configure logging (same as original)
logging.basicConfig(
    filename='youtube_summarizer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Import the model prices and backend functions from original script
from functions import (
    model_prices,
    extract_video_id,
    get_transcript,
    detect_language,
    summarize_text
)

def copy_to_clipboard(summary_text):
    """Copy summary text to clipboard"""
    if not summary_text:
        return "No text to copy"
    
    try:
        pyperclip.copy(summary_text)
        return "Text copied to clipboard"
    except Exception as e:
        return f"Error copying to clipboard: {str(e)}"

def process_summary(youtube_url, api_key, selected_model, output_language, summary_type, custom_prompt=""):
    """
    Unified function to handle all types of summaries
    """
    if not youtube_url or not api_key:
        return "Please provide both YouTube URL and API key.", "No summary generated."

    openai.api_key = api_key

    # Extract video ID
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return "Invalid YouTube URL. Please check and try again.", "No summary generated."

    # Fetch transcript
    transcript, transcript_language = get_transcript(video_id)
    if not transcript:
        return "Failed to retrieve transcript.", "No summary generated."

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
        response = openai.chat.completions.create(
            model=selected_model,
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
        model_used = selected_model
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        # Calculate cost
        if model_used in model_prices:
            prompt_cost = (prompt_tokens / 1000) * model_prices[model_used]['prompt']
            completion_cost = (completion_tokens / 1000) * model_prices[model_used]['completion']
            total_cost = round(prompt_cost + completion_cost, 6)
        else:
            total_cost = None


        expected_cost_krw = round(total_cost * 1378.28) if total_cost is not None else 'N/A'
        # Prepare additional info
        additional_info = (
            f"Expected Cost (KRW): ₩{expected_cost_krw}\n"
            f"Expected Cost (USD): ${total_cost if total_cost is not None else 'N/A'}\n"
            f"Tokens Used:\n"
            f"  - Prompt Tokens: {prompt_tokens}\n"
            f"  - Completion Tokens: {completion_tokens}\n"
            f"  - Total Tokens: {total_tokens}\n"
            
        )

        return summary, additional_info

    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        return f"Error generating summary: {str(e)}", "Error occurred"

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
                label="OpenAI API Key",
                placeholder="Enter your OpenAI API key here...",
                type="password"
            )

        with gr.Row():
            model_dropdown = gr.Dropdown(
                choices=list(model_prices.keys()),
                value="chatgpt-4o-latest" if "chatgpt-4o-latest" in model_prices else list(model_prices.keys())[0],
                label="GPT Model"
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

        # Submit button
        with gr.Row():
            submit_btn = gr.Button("Submit", visible=False)

        # Move paste and copy buttons above the summary buttons
        with gr.Row():
            paste_url_btn = gr.Button("Paste in YouTube Link")
            copy_btn = gr.Button("Copy Output")

        with gr.Row():
            full_summary_btn = gr.Button("Full Summary")
            short_summary_btn = gr.Button("Short Summary")
            custom_prompt_btn = gr.Button("Custom Prompt")

        # Output areas
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

        # Add function to paste URL from clipboard
        def paste_from_clipboard():
            try:
                return pyperclip.paste()
            except Exception as e:
                return f"Error pasting from clipboard: {str(e)}"

        # Add click handler for paste button
        paste_url_btn.click(
            fn=paste_from_clipboard,
            inputs=[],
            outputs=[youtube_url]
        )

        # Update process_and_show_buttons to remove file-related outputs
        def process_and_show_buttons(*args, **kwargs):
            summary, info = process_summary(*args, **kwargs)
            return [
                summary,
                info,
                gr.update(visible=True),  # copy_btn
            ]

        # Update the click handlers to remove file-related outputs
        submit_btn.click(
            fn=lambda url, key, model, lang, prompt: process_and_show_buttons(
                url, key, model, lang, "custom", prompt
            ),
            inputs=[youtube_url, api_key, model_dropdown, language_dropdown, custom_prompt],
            outputs=[
                summary_output,
                additional_info,
                copy_btn
            ]
        )

        # Update copy button to return None (no status output)
        copy_btn.click(
            fn=copy_to_clipboard,
            inputs=[summary_output],
            outputs=None,
            api_name="copy"
        )

        # Add these click handlers for the custom prompt button and copy button
        custom_prompt_btn.click(
            fn=lambda: (
                gr.update(visible=True),  # Show custom prompt
                gr.update(visible=True)   # Show submit button
            ),
            inputs=[],
            outputs=[custom_prompt, submit_btn]
        )

        # Add the copy button click handler
        copy_btn.click(
            fn=copy_to_clipboard,
            inputs=[summary_output],
            outputs=None,
            api_name="copy"
        )

        # Update the full and short summary buttons to hide custom prompt
        full_summary_btn.click(
            fn=lambda url, key, model, lang: process_and_show_buttons(
                url, key, model, lang, "full", ""
            ),
            inputs=[youtube_url, api_key, model_dropdown, language_dropdown],
            outputs=[
                summary_output,
                additional_info,
                copy_btn
            ]
        )

        short_summary_btn.click(
            fn=lambda url, key, model, lang: process_and_show_buttons(
                url, key, model, lang, "short", ""
            ),
            inputs=[youtube_url, api_key, model_dropdown, language_dropdown],
            outputs=[
                summary_output,
                additional_info,
                copy_btn
            ]
        )

        return demo

if __name__ == "__main__":
    demo = create_gradio_interface()
    demo.launch(
        share=True,
        inbrowser=True,
        debug=True
    ) 