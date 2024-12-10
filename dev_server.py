import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.yt_summ_gradio:app", host="0.0.0.0", port=8000, reload=True)