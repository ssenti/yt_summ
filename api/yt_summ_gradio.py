import gradio as gr

def summarize_youtube_video(url):
    # Your summarization logic here
    return "Summary of the video."

app = gr.Interface(fn=summarize_youtube_video, inputs="text", outputs="text")

def handler(request):
    return app(request)

# Vercel expects a callable named `handler` 