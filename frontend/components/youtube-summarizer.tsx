'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import ReactMarkdown from 'react-markdown'

// Common languages list
const LANGUAGES = [
  { code: "zh", name: "Mandarin Chinese" },
  { code: "hi", name: "Hindi" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "ar", name: "Standard Arabic" },
  { code: "bn", name: "Bengali" },
  { code: "pt", name: "Portuguese" },
  { code: "ru", name: "Russian" },
  { code: "ur", name: "Urdu" },
  { code: "id", name: "Indonesian" },
  { code: "de", name: "German" },
  { code: "ja", name: "Japanese" },
  { code: "sw", name: "Swahili" },
  { code: "mr", name: "Marathi" },
  { code: "te", name: "Telugu" },
  { code: "tr", name: "Turkish" },
  { code: "ta", name: "Tamil" },
  { code: "vi", name: "Vietnamese" },
  { code: "ko", name: "Korean" },
  { code: "it", name: "Italian" },
  { code: "pa", name: "Punjabi" },
  { code: "gu", name: "Gujarati" },
  { code: "fa", name: "Persian (Farsi)" },
  { code: "th", name: "Thai" },
  { code: "pl", name: "Polish" },
  { code: "uk", name: "Ukrainian" },
  { code: "ms", name: "Malay" },
  { code: "kn", name: "Kannada" },
  { code: "ha", name: "Hausa" }
] as const;

type LanguageCode = typeof LANGUAGES[number]['code']

function useKeyboardShortcut(key: string, callback: () => void, metaKey: boolean = true, shiftKey: boolean = false) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.key.toLowerCase() === key.toLowerCase() && 
        event.metaKey === metaKey &&
        event.shiftKey === shiftKey
      ) {
        event.preventDefault()
        callback()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [key, callback, metaKey, shiftKey])
}

interface SummaryResponse {
  success: boolean;
  summary: string;
  additional_info: string;
}

export default function YoutubeSummarizer() {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [outputLanguage, setOutputLanguage] = useState<'english' | 'korean' | LanguageCode>('english')
  const [showCustomPrompt, setShowCustomPrompt] = useState(false)
  const [customPrompt, setCustomPrompt] = useState('')
  const [summary, setSummary] = useState('')
  const [additionalInfo, setAdditionalInfo] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [loadingTime, setLoadingTime] = useState(0)
  const loadingInterval = useRef<NodeJS.Timeout>()

  const customPromptRef = useRef<HTMLTextAreaElement>(null)

  // Clean up interval on unmount
  useEffect(() => {
    return () => {
      if (loadingInterval.current) {
        clearInterval(loadingInterval.current)
      }
    }
  }, [])

  const API_URL = process.env.NODE_ENV === 'development' 
    ? 'http://localhost:8000' 
    : '/api'

  const handleSummarize = async (summaryType: string) => {
    if (!youtubeUrl || !apiKey) {
      setError('Please provide both YouTube URL and API key')
      return
    }

    setIsLoading(true)
    setError('')
    setSummary('')
    setAdditionalInfo('')
    setLoadingTime(0)

    // Start the loading timer
    const startTime = Date.now()
    loadingInterval.current = setInterval(() => {
      setLoadingTime(Math.round((Date.now() - startTime) / 100) / 10)
    }, 100)

    try {
      const response = await fetch(`${API_URL}/api/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtube_url: youtubeUrl,
          api_key: apiKey,
          output_language: outputLanguage,
          summary_type: summaryType,
          custom_prompt: summaryType === 'custom' ? customPrompt : '',
        }),
      })

      const data: SummaryResponse = await response.json()

      if (data.success) {
        setSummary(data.summary)
        setAdditionalInfo(data.additional_info)
      } else {
        setError('Failed to generate summary')
      }
    } catch (err) {
      setError('An error occurred while generating the summary')
      console.error(err)
    } finally {
      setIsLoading(false)
      if (loadingInterval.current) {
        clearInterval(loadingInterval.current)
      }
    }
  }

  const handleFullSummary = () => handleSummarize('full')
  const handleShortSummary = () => handleSummarize('short')
  const handleSubmitPrompt = () => handleSummarize('custom')

  const handleCustomPrompt = () => {
    setShowCustomPrompt(true)
    setTimeout(() => {
      customPromptRef.current?.focus()
    }, 0)
  }

  const handlePasteYoutubeUrl = async () => {
    try {
      const text = await navigator.clipboard.readText()
      setYoutubeUrl(text)
    } catch (err) {
      setError('Failed to paste from clipboard. Please paste manually.')
    }
  }

  useKeyboardShortcut('f', handleFullSummary)
  useKeyboardShortcut('s', handleShortSummary)
  useKeyboardShortcut('p', handleCustomPrompt)
  useKeyboardShortcut('v', handlePasteYoutubeUrl, true, true)
  useKeyboardShortcut('enter', () => {
    if (showCustomPrompt && customPrompt) {
      handleSubmitPrompt()
    }
  })

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-3xl font-bold text-center mb-8">Youtube Video Summarizer</h1>
      
      <div className="space-y-4">
        <div>
          <Label htmlFor="youtube-url">Youtube URL</Label>
          <div className="flex gap-2">
            <Input 
              id="youtube-url" 
              placeholder="https://www.youtube.com/watch?v=..." 
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
            />
            <Button 
              onClick={handlePasteYoutubeUrl}
              className="bg-black hover:bg-black/90 text-white text-sm font-medium"
            >
              Paste Youtube URL (⌘⇧V)
            </Button>
          </div>
        </div>
        
        <div>
          <Label htmlFor="api-key">xAI API Key</Label>
          <Input 
            id="api-key" 
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Ask Crimson if confused..."
          />
        </div>
        
        <div>
          <Label>Output Language</Label>
          <div className="flex items-center gap-4">
            <RadioGroup 
              value={outputLanguage}
              onValueChange={(value: 'english' | 'korean') => setOutputLanguage(value)}
              className="flex gap-4"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="english" id="english" />
                <Label htmlFor="english">English</Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="korean" id="korean" />
                <Label htmlFor="korean">Korean</Label>
              </div>
            </RadioGroup>
            
            <Select
              value={LANGUAGES.some(lang => lang.code === outputLanguage) ? outputLanguage as string : undefined}
              onValueChange={(value: LanguageCode) => setOutputLanguage(value)}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Other Languages" />
              </SelectTrigger>
              <SelectContent className="w-[200px]">
                {LANGUAGES.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code} className="truncate">
                    {lang.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <div className="grid grid-cols-4 gap-2">
          <Button 
            onClick={handleFullSummary} 
            disabled={isLoading}
            className="bg-black hover:bg-black/90 text-white text-sm font-medium"
          >
            {isLoading ? 'Generating...' : 'Full Summary (⌘F)'}
          </Button>
          <Button 
            onClick={handleShortSummary}
            disabled={isLoading}
            className="bg-black hover:bg-black/90 text-white text-sm font-medium"
          >
            {isLoading ? 'Generating...' : 'Short Summary (⌘S)'}
          </Button>
          <Button 
            onClick={handleCustomPrompt}
            disabled={isLoading}
            className="bg-black hover:bg-black/90 text-white text-sm font-medium"
          >
            Custom Prompt (⌘P)
          </Button>
          {showCustomPrompt && (
            <Button 
              onClick={handleSubmitPrompt}
              disabled={isLoading}
              className="bg-black hover:bg-black/90 text-white text-sm font-medium"
            >
              {isLoading ? 'Generating...' : 'Submit Prompt (⌘Ent)'}
            </Button>
          )}
        </div>
        
        {showCustomPrompt && (
          <div className="space-y-2">
            <Label htmlFor="custom-prompt">Custom Prompt (Optional)</Label>
            <Textarea 
              id="custom-prompt" 
              placeholder="Enter your custom prompt here..."
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              ref={customPromptRef}
            />
          </div>
        )}
        
        {error && (
          <div className="text-red-500 text-sm">
            {error}
          </div>
        )}
        
        <div>
          <Label htmlFor="summary">Summary {isLoading && `(Loading... ${loadingTime}s)`}</Label>
          <div className="flex min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
            {summary ? (
              <ReactMarkdown className="prose prose-sm dark:prose-invert w-full prose-headings:font-bold prose-strong:text-black dark:prose-strong:text-white prose-ul:list-disc prose-ol:list-decimal">
                {summary}
              </ReactMarkdown>
            ) : (
              <p className="text-muted-foreground">
                {isLoading ? "Generating summary..." : "Summary will appear here..."}
              </p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="additional-info">Additional Information</Label>
          <div className="min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
            {additionalInfo ? (
              <ReactMarkdown className="prose prose-sm dark:prose-invert w-full prose-headings:font-bold prose-strong:text-black dark:prose-strong:text-white prose-ul:list-disc prose-ol:list-decimal">
                {additionalInfo}
              </ReactMarkdown>
            ) : (
              <p className="text-muted-foreground">
                Additional information will appear here...
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

