'use client'

import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Textarea } from "@/components/ui/textarea"

function useKeyboardShortcut(key: string, callback: () => void, metaKey: boolean = true) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === key.toLowerCase() && event.metaKey === metaKey) {
        event.preventDefault()
        callback()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [key, callback, metaKey])
}

interface SummaryResponse {
  success: boolean;
  summary: string;
  additional_info: string;
}

export default function YoutubeSummarizer() {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [outputLanguage, setOutputLanguage] = useState('english')
  const [showCustomPrompt, setShowCustomPrompt] = useState(false)
  const [customPrompt, setCustomPrompt] = useState('')
  const [summary, setSummary] = useState('')
  const [additionalInfo, setAdditionalInfo] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

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

    try {
      const response = await fetch(`${API_URL}/api/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtube_url: youtubeUrl,
          api_key: apiKey,
          output_language: outputLanguage === 'english' ? 'English' : 'Original Language',
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
    }
  }

  const handleFullSummary = () => handleSummarize('full')
  const handleShortSummary = () => handleSummarize('short')
  const handleSubmitPrompt = () => handleSummarize('custom')

  const handleCustomPrompt = () => {
    setShowCustomPrompt(true)
  }

  useKeyboardShortcut('f', handleFullSummary)
  useKeyboardShortcut('s', handleShortSummary)
  useKeyboardShortcut('p', handleCustomPrompt)

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-3xl font-bold text-center mb-8">Youtube Transcript Summarizer</h1>
      
      <div className="space-y-4">
        <div>
          <Label htmlFor="youtube-url">Youtube Video URL</Label>
          <Input 
            id="youtube-url" 
            placeholder="https://www.youtube.com/watch?v=..." 
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
          />
        </div>
        
        <div>
          <Label htmlFor="api-key">API Key</Label>
          <Input 
            id="api-key" 
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>
        
        <div>
          <Label>Output Language</Label>
          <RadioGroup 
            value={outputLanguage} 
            onValueChange={setOutputLanguage}
            className="flex space-x-4"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="english" id="english" />
              <Label htmlFor="english">English</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="original" id="original" />
              <Label htmlFor="original">Original Language</Label>
            </div>
          </RadioGroup>
        </div>
        
        <div className="space-x-4">
          <Button 
            onClick={handleFullSummary} 
            disabled={isLoading}
          >
            {isLoading ? 'Generating...' : 'Full Summary (⌘F)'}
          </Button>
          <Button 
            onClick={handleShortSummary}
            disabled={isLoading}
          >
            {isLoading ? 'Generating...' : 'Short Summary (⌘S)'}
          </Button>
          <Button 
            onClick={handleCustomPrompt}
            disabled={isLoading}
          >
            Custom Prompt (⌘P)
          </Button>
        </div>
        
        {showCustomPrompt && (
          <div className="space-y-2">
            <Label htmlFor="custom-prompt">Custom Prompt (Optional)</Label>
            <Textarea 
              id="custom-prompt" 
              placeholder="Enter your custom prompt here..."
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
            />
            <Button 
              onClick={handleSubmitPrompt}
              disabled={isLoading}
            >
              {isLoading ? 'Generating...' : 'Submit Prompt'}
            </Button>
          </div>
        )}
        
        {error && (
          <div className="text-red-500 text-sm">
            {error}
          </div>
        )}
        
        <div>
          <Label htmlFor="summary">Summary</Label>
          <Textarea 
            id="summary" 
            placeholder="Summary will appear here..." 
            value={summary}
            readOnly 
            className="h-48"
          />
        </div>
        
        <div>
          <Label htmlFor="additional-info">Additional Information</Label>
          <Textarea 
            id="additional-info" 
            placeholder="Additional information will appear here..." 
            value={additionalInfo}
            readOnly 
            className="h-32"
          />
        </div>
      </div>
    </div>
  )
}

