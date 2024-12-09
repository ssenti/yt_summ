---
title: yt_summ
emoji: 🤗
colorFrom: indigo
colorTo: green
sdk: gradio
app_file: yt_summ_gradio.py
pinned: false
short_description: youtube video summarization tool
license: mit
---

# YouTube Video Summarizer (yt_summ) 🤗

A web application that generates summaries of YouTube videos using an LLM

## Features

- Generate full, concise (4 bullet points), or custom summaries of YouTube videos
- Currently default LLM is X.AI's Grok model, because it gives free $25 credits per month :)
- Support for multiple languages (auto-detection and English output), though think it's currently not available for Grok
- Copy summaries to clipboard
- Token usage tracking
- Clean and intuitive Gradio interface

## Requirements

- Python 3.6+
- X.AI API key (starts with 'xai-'): ask Crimson for his API key for now if you don't know how to get it
- Required packages:
  - gradio==5.4.0
  - openai==1.12.0
  - youtube_transcript_api==0.6.2
  - python-dotenv==1.0.1
  - langdetect==1.0.9
  - pyperclip==1.8.2
  - fpdf==1.7.2
  - fpdf2==2.7.6

## Installation

1. Clone the repository
2. Install dependencies:
'''bash
pip install -r requirements.txt
'''

## Usage

1. Run the application:
'''bash
python yt_summ_gradio.py
'''
2. Enter a YouTube URL and your X.AI API key
3. Choose your desired summary type:
   - Full Summary
   - Short Summary (4 sentences)
   - Custom Prompt (and then press Submit Prompt)