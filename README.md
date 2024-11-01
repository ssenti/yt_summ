# Youtube Transcript Summarizer

title: "Youtube Transcript Summarizer"   
emoji: "🚀"                            
colorFrom: "blue"                      
colorTo: "green"                  
sdk: "gradio"                       
sdk_version: "5.4"                    
app_file: yt_summ_gradio.py          
pinned: true                

## Usage

1. Clone the repo:
```bash
git clone https://github.com/ssenti/youtube_summary_gardio
cd youtube-transcript-summarizer
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python yt_summ_gradio.py
```

4. Open your web browser and navigate to the local URL shown in the terminal (something like http://localhost:3000)

5. Enter:
   - YouTube video URL
   - Your OpenAI API key
   - Select desired GPT model
   - Choose output language
   - Select summary type (Full/Short/Custom)

6. Outputs a summary

## Summary Types

- **Full Summary**: Comprehensive summary of the video content
- **Short Summary**: Concise 4-sentence summary in bullet points
- **Custom Prompt**: Create a custom summary using your own prompt

## Features in Detail

### Clipboard Integration
- Paste YouTube URLs directly from clipboard
- Copy generated summaries to clipboard

### Model Selection
- Choose from various GPT models (GPT-4, GPT-3.5-Turbo, etc.)
- Each model has different pricing and capabilities

### Language Options
- Output in English (default)
- Output in the original transcript language

### Cost Tracking
- Real-time cost estimation in USD and KRW
- Token usage breakdown:
  - Prompt tokens
  - Completion tokens
  - Total tokens used

## Error Handling

The application includes robust error handling for:
- Invalid YouTube URLs
- Missing API keys
- Failed transcript retrieval
- API errors

## Logging

All operations are logged to `youtube_summarizer.log` for debugging and monitoring.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Acknowledgments

- OpenAI for GPT API
- Gradio for the web interface
- YouTube for transcript access
