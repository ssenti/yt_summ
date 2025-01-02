import { NextRequest } from 'next/server';
import OpenAI from 'openai';
import { YoutubeTranscript } from 'youtube-transcript';
import type { SummaryRequest, SummaryResponse, ErrorResponse } from '@/app/types/api';

export const runtime = 'edge';

function extractVideoId(url: string): string | null {
  const patterns = [
    /(?:v=|\/)([0-9A-Za-z_-]{11}).*/,
    /(?:youtu\.be\/)([0-9A-Za-z_-]{11})/,
    /(?:embed\/)([0-9A-Za-z_-]{11})/
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) {
      return match[1];
    }
  }
  return null;
}

interface TranscriptSegment {
  text: string;
  duration: number;
  offset: number;
}

async function getTranscript(videoId: string): Promise<[string | null, string | null]> {
  try {
    const transcript = await YoutubeTranscript.fetchTranscript(videoId);
    const fullText = transcript.map((t: TranscriptSegment) => t.text).join(' ');
    return [fullText, null];
  } catch (error) {
    return [null, error instanceof Error ? error.message : 'Failed to fetch transcript'];
  }
}

function createSystemMessage(targetLanguage: string): string {
  return `You are a helpful assistant that provides an accurate and relevant response to a user prompt, based on a video transcript they provide. Make sure your response sounds natural and fluent in ${targetLanguage}.`;
}

function createPrompt(transcript: string, summaryType: string, targetLanguage: string, customPrompt?: string): string {
  if (summaryType === 'short') {
    return `Please provide a very concise summary of the following transcript in ${targetLanguage}. Format your response as plain bullet points (without bold formatting), using a maximum of 4 sentences:\n\n${transcript}`;
  } else if (summaryType === 'custom' && customPrompt) {
    return `Please provide your response in ${targetLanguage}. User prompt:\n\n${customPrompt}\n\n\n\nTranscript:\n\n${transcript}`;
  } else {
    return `Please provide a detailed full summary of the following transcript. Provide the summary in ${targetLanguage}:\n\n${transcript}`;
  }
}

interface LLMConfig {
  model: string;
  baseURL: string;
}

const LLM_CONFIGS: Record<string, LLMConfig> = {
  deepseek: {
    model: 'deepseek-chat',
    baseURL: 'https://api.deepseek.com'
  },
  gemini: {
    model: 'gemini-2.0-flash-exp',
    baseURL: 'https://generativelanguage.googleapis.com/v1beta/'
  },
  xai: {
    model: 'grok-2-1212',
    baseURL: 'https://api.x.ai/v1'
  },
  openai: {
    model: 'gpt-4o',
    baseURL: 'https://api.openai.com/v1'
  }
};

export async function POST(request: NextRequest) {
  try {
    const data: SummaryRequest = await request.json();
    const { youtube_url, api_key, output_language, summary_type, custom_prompt, llm_provider } = data;

    if (!youtube_url || !api_key) {
      return new Response(
        JSON.stringify({ detail: 'Please provide both YouTube URL and API key' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }


    const videoId = extractVideoId(youtube_url);
    if (!videoId) {
      return new Response(
        JSON.stringify({ detail: 'Invalid YouTube URL. Please check and try again.' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const [transcript, error] = await getTranscript(videoId);
    if (!transcript) {
      return new Response(
        JSON.stringify({ detail: `Failed to retrieve transcript: ${error}` }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const config = LLM_CONFIGS[llm_provider];
    if (!config) {
      return new Response(
        JSON.stringify({ detail: 'Invalid LLM provider selected' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const client = new OpenAI({
      apiKey: api_key,
      baseURL: config.baseURL
    });

    const response = await client.chat.completions.create({
      model: config.model,
      messages: [
        { role: 'system', content: createSystemMessage(output_language) },
        { role: 'user', content: createPrompt(transcript, summary_type, output_language, custom_prompt) }
      ],
      max_tokens: 2048,
      temperature: 0.7,
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error('No response content from API');
    }

    const result: SummaryResponse = {
      success: true,
      summary: content.trim(),
      model: config.model,
      tokens: {
        total: response.usage?.total_tokens || 0,
        prompt: response.usage?.prompt_tokens || 0,
        completion: response.usage?.completion_tokens || 0
      }
    };

    return new Response(
      JSON.stringify(result),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error in summarize endpoint:', error);
    const errorResponse: ErrorResponse = {
      detail: error instanceof Error ? error.message : 'An unexpected error occurred'
    };
    return new Response(
      JSON.stringify(errorResponse),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
} 