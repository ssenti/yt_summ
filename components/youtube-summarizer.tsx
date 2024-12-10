'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import ReactMarkdown from 'react-markdown'
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut'
import type { SummaryResponse, ErrorResponse } from '@/types/api'

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

interface FeatureRequest {
  request_text: string;
  requester_name: string;
  timestamp: string;
}

// Add this near the feature request section
const GITHUB_REPO_URL = 'https://github.com/ssenti/yt_summ_gradio/issues?q=is%3Aissue+label%3Afeature-request';

export default function YoutubeSummarizer() {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [outputLanguage, setOutputLanguage] = useState<'english' | 'korean' | LanguageCode>('english')
  const [customPrompt, setCustomPrompt] = useState('')
  const [summary, setSummary] = useState('')
  const [response, setResponse] = useState<SummaryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [loadingTime, setLoadingTime] = useState(0)
  const [featureRequest, setFeatureRequest] = useState('')
  const [requesterName, setRequesterName] = useState('')
  const [featureRequests, setFeatureRequests] = useState<FeatureRequest[]>([])
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

  // Load existing feature requests
  useEffect(() => {
    const loadFeatureRequests = async () => {
      try {
        const response = await fetch('/api/feature-request')
        const data = await response.json()
        if (data.requests) {
          setFeatureRequests(data.requests)
        }
      } catch (error) {
        console.error('Error loading feature requests:', error)
      }
    }
    loadFeatureRequests()
  }, [])

  const handleSummarize = async (summaryType: 'short' | 'detailed' | 'custom') => {
    if (!youtubeUrl || !apiKey) {
      setError('Please provide both YouTube Video URL and API key')
      return
    }

    setIsLoading(true)
    setError('')
    setSummary('')
    setResponse(null)
    setLoadingTime(0)

    // Start the loading timer
    const startTime = Date.now()
    loadingInterval.current = setInterval(() => {
      setLoadingTime(Math.round((Date.now() - startTime) / 100) / 10)
    }, 100)

    try {
      const response = await fetch('/api/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtube_url: youtubeUrl,
          api_key: apiKey,
          output_language: outputLanguage,
          summary_type: summaryType,
          custom_prompt: summaryType === 'custom' ? customPrompt : undefined,
        }),
      })

      const data = await response.json() as SummaryResponse;

      if (response.ok && data.success) {
        setSummary(data.summary)
        setResponse(data)
      } else {
        setError('Failed to generate summary. Please check your API key and YouTube URL.')
      }
    } catch (error) {
      console.error('Summary generation error:', error)
      setError('Network error or server is not responding.')
    } finally {
      setIsLoading(false)
      if (loadingInterval.current) {
        clearInterval(loadingInterval.current)
      }
    }
  }

  const handleFullSummary = () => handleSummarize('detailed')
  const handleShortSummary = () => handleSummarize('short')
  const handleSubmitPrompt = () => handleSummarize('custom')

  const handlePasteYoutubeUrl = async () => {
    try {
      const text = await navigator.clipboard.readText()
      setYoutubeUrl(text)
    } catch (error) {
      setError('Failed to paste from clipboard. Please paste manually.')
      console.error('Clipboard error:', error)
    }
  }

  const handleFeatureRequest = async () => {
    if (featureRequest.trim()) {
      try {
        const response = await fetch('/api/feature-request', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            request_text: featureRequest.trim(),
            requester_name: requesterName.trim() || 'Anonymous'
          }),
        })

        if (response.ok) {
          // Add the new request to the local state with current timestamp
          const newRequest: FeatureRequest = {
            request_text: featureRequest.trim(),
            requester_name: requesterName.trim() || 'Anonymous',
            timestamp: new Date().toISOString()
          }
          setFeatureRequests(prev => [...prev, newRequest])
          setFeatureRequest('')
          setRequesterName('')
        } else {
          console.error('Failed to save feature request')
        }
      } catch (error) {
        console.error('Error saving feature request:', error)
      }
    }
  }

  // Update keyboard shortcuts
  useKeyboardShortcut({ key: 'f', callback: handleFullSummary })
  useKeyboardShortcut({ key: 's', callback: handleShortSummary })
  useKeyboardShortcut({ key: 'p', callback: () => {
    if (customPrompt.trim()) {
      handleSubmitPrompt()
    }
  }})
  useKeyboardShortcut({ key: 'enter', callback: handlePasteYoutubeUrl })

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="font-geist-sans text-5xl font-black text-center mb-8 tracking-tight">
        <span className="bg-gradient-to-r from-red-600 via-red-500 to-red-400 bg-clip-text text-transparent">
          YouTube{" "}
        </span>
        <span className="bg-gradient-to-r from-gray-900 via-black to-gray-800 bg-clip-text text-transparent">
          Summarizer
        </span>
      </h1>
      
      <div className="space-y-4">
        <div>
          <Label htmlFor="youtube-url" className="font-bold">YouTube Video URL</Label>
          <div className="flex gap-2">
            <Input 
              id="youtube-url" 
              placeholder="https://www.youtube.com/watch?v=..." 
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              className="flex-1"
            />
            <Button 
              onClick={handlePasteYoutubeUrl}
              className="bg-black hover:bg-black/90 text-white text-sm font-medium w-[23%]"
            >
              Paste URL (⌘Enter)
            </Button>
          </div>
        </div>
        
        <div>
          <Label htmlFor="api-key" className="font-bold">xAI API Key</Label>
          <Input 
            id="api-key" 
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="xAI is currently giving out free credits..."
          />
        </div>
        
        <div>
          <Label className="font-bold">Output Language</Label>
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
        
        <div className="grid grid-cols-3 gap-2">
          <Button 
            onClick={handleFullSummary} 
            disabled={isLoading}
            className="bg-black hover:bg-black/90 text-white text-sm font-medium w-full"
          >
            {isLoading ? 'Generating...' : 'Full Summary (⌘F)'}
          </Button>
          <Button 
            onClick={handleShortSummary}
            disabled={isLoading}
            className="bg-black hover:bg-black/90 text-white text-sm font-medium w-full"
          >
            {isLoading ? 'Generating...' : 'Short Summary (⌘S)'}
          </Button>
          <Button 
            onClick={handleSubmitPrompt}
            disabled={isLoading || !customPrompt.trim()}
            className="bg-black hover:bg-black/90 text-white text-sm font-medium w-full"
          >
            {isLoading ? 'Generating...' : 'Submit Custom Prompt (⌘P)'}
          </Button>
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="custom-prompt" className="font-bold">Custom Prompt (Optional)</Label>
          <Textarea 
            id="custom-prompt" 
            placeholder="Enter your custom prompt here and then press submit..."
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            ref={customPromptRef}
            className="h-[100px] resize-none overflow-y-auto"
          />
        </div>
        
        {error && (
          <div className="text-red-500 text-sm">
            {error}
          </div>
        )}
        
        <div>
          <Label htmlFor="summary" className="font-bold">Summary {isLoading && `(Loading... ${loadingTime}s)`}</Label>
          <div className="h-[400px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 overflow-y-auto">
            {summary ? (
              <div className="w-full">
                <ReactMarkdown 
                  className="prose prose-sm dark:prose-invert max-w-none prose-p:font-normal prose-p:my-1 prose-li:my-0 prose-ul:my-1 prose-ol:my-1 prose-headings:font-bold prose-strong:font-semibold prose-strong:text-black dark:prose-strong:text-white prose-ul:list-disc prose-ol:list-decimal"
                >
                  {summary}
                </ReactMarkdown>
              </div>
            ) : (
              <p className="text-muted-foreground">
                {isLoading ? "Generating summary..." : "Summary will appear here..."}
              </p>
            )}
          </div>
        </div>
        
        <div>
          <Label htmlFor="additional-info" className="font-bold">Processing Info</Label>
          <div className="h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 overflow-y-auto">
            {summary ? (
              <div className="space-y-1">
                <p><span className="font-semibold">Model:</span> {response?.model || 'grok-beta'}</p>
                <p><span className="font-semibold">Total Tokens:</span> {response?.tokens?.total || 0}</p>
                <ul className="list-none pl-4 space-y-0.5">
                  <li>
                    <span className="font-medium">- Prompt Tokens:</span> {response?.tokens?.prompt || 0}
                  </li>
                  <li>
                    <span className="font-medium">- Completion Tokens:</span> {response?.tokens?.completion || 0}
                  </li>
                </ul>
              </div>
            ) : (
              <p className="text-muted-foreground">
                Processing information will appear here...
              </p>
            )}
          </div>
        </div>

        {/* Feature Request Section */}
        <div className="grid grid-cols-2 gap-4">
          {/* Feature Request Input */}
          <div>
            <div className="flex justify-between items-center gap-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="feature-request" className="font-bold whitespace-nowrap">Feature Request By</Label>
                <Input
                  id="requester-name"
                  placeholder="name"
                  value={requesterName}
                  onChange={(e) => setRequesterName(e.target.value)}
                  className="w-28 h-7 text-xs"
                />
              </div>
              <Button 
                onClick={handleFeatureRequest}
                disabled={!featureRequest.trim()}
                className="bg-black hover:bg-black/90 text-white text-xs font-medium h-7 px-3"
              >
                Send
              </Button>
            </div>
            <div className="mt-2">
              <Textarea 
                id="feature-request" 
                placeholder="Feel free to request new features here, it will be sent to Crimson’s github repo as an issue…" 
                value={featureRequest}
                onChange={(e) => setFeatureRequest(e.target.value)}
                className="h-[200px] resize-none overflow-y-auto"
              />
            </div>
          </div>

          {/* Feature Request List */}
          <div>
            <div className="flex justify-between items-center gap-2">
              <Label className="font-bold">Feature Request List</Label>
              <Input
                className="w-28 h-7 text-xs invisible"
                disabled
              />
            </div>
            <div className="mt-2">
              <div className="h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background overflow-y-auto">
                {featureRequests.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-2">
                    {[...featureRequests]
                      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                      .map((request, index) => (
                        <li key={index} className="text-sm">
                          <span>{request.request_text}</span>
                          <div className="text-xs text-gray-500 mt-1">
                            <span>By: {request.requester_name}</span>
                            <span className="ml-2">
                              {new Date(request.timestamp).toLocaleString()}
                            </span>
                          </div>
                        </li>
                      ))}
                  </ul>
                ) : (
                  <div className="text-muted-foreground">
                    <p>Feature requests will appear here...</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

