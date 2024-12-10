import { NextRequest } from 'next/server';

interface FeatureRequest {
  request_text: string;
  requester_name: string;
  timestamp: string;
}

interface GitHubIssue {
  number: number;
  title: string;
  body: string;
  created_at: string;
  html_url: string;
  labels: Array<{
    name: string;
    color: string;
  }>;
}

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO || 'yt_summ_gradio';
const GITHUB_OWNER = process.env.GITHUB_OWNER;

// Cache for feature requests (still useful for quick reads)
const featureRequests: FeatureRequest[] = [];

async function createGitHubIssue(title: string, body: string) {
  if (!GITHUB_TOKEN || !GITHUB_OWNER) {
    console.error('GitHub configuration:', {
      token: GITHUB_TOKEN ? 'present' : 'missing',
      owner: GITHUB_OWNER ? 'present' : 'missing',
      repo: GITHUB_REPO
    });
    throw new Error('GitHub configuration is missing');
  }

  console.log('Creating GitHub issue:', {
    owner: GITHUB_OWNER,
    repo: GITHUB_REPO,
    title,
    hasBody: !!body
  });

  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues`;
  console.log('GitHub API URL:', url);

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title,
        body,
        labels: ['feature-request']
      })
    });

    if (!response.ok) {
      const errorData = await response.text();
      console.error('GitHub API Error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorData
      });
      throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
    }

    const data = (await response.json()) as GitHubIssue;
    console.log('GitHub issue created:', {
      issueNumber: data.number,
      url: data.html_url
    });
    return data;
  } catch (error) {
    console.error('Error in createGitHubIssue:', error);
    throw error;
  }
}

async function getGitHubIssues(): Promise<FeatureRequest[]> {
  if (!GITHUB_TOKEN || !GITHUB_OWNER) {
    throw new Error('GitHub configuration is missing');
  }

  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/issues?labels=feature-request&state=open`;
  console.log('Fetching GitHub issues:', url);

  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
      }
    });

    if (!response.ok) {
      const errorData = await response.text();
      console.error('GitHub API Error:', {
        status: response.status,
        statusText: response.statusText,
        error: errorData
      });
      throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
    }

    const issues = (await response.json()) as GitHubIssue[];
    console.log('Fetched issues count:', issues.length);
    return issues.map((issue) => ({
      request_text: issue.body,
      requester_name: issue.title.split(' by ')[1] || 'Anonymous',
      timestamp: issue.created_at
    }));
  } catch (error) {
    console.error('Error in getGitHubIssues:', error);
    throw error;
  }
}

export async function GET() {
  try {
    console.log('GET: Fetching feature requests');
    const requests = await getGitHubIssues();
    return new Response(
      JSON.stringify({ requests }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('GET: Failed to fetch feature requests:', error);
    // Fallback to cached requests if GitHub API fails
    return new Response(
      JSON.stringify({ requests: featureRequests }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    console.log('POST: Processing new feature request');
    const { request_text, requester_name } = await request.json();
    
    if (!request_text?.trim()) {
      return new Response(
        JSON.stringify({ detail: 'Request text is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const newRequest: FeatureRequest = {
      request_text: request_text.trim(),
      requester_name: requester_name?.trim() || 'Anonymous',
      timestamp: new Date().toISOString()
    };

    // Add to local cache
    featureRequests.push(newRequest);
    console.log('Added to local cache');

    // Create GitHub issue
    try {
      console.log('Creating GitHub issue for request');
      const issue = await createGitHubIssue(
        `Feature Request by ${newRequest.requester_name}`,
        newRequest.request_text
      );
      console.log('GitHub issue created successfully:', issue);
    } catch (error) {
      console.error('Failed to create GitHub issue:', error);
      // Return error response if GitHub integration fails
      return new Response(
        JSON.stringify({ detail: 'Failed to create GitHub issue' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({ success: true }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('POST: Failed to process feature request:', error);
    return new Response(
      JSON.stringify({ detail: 'Failed to process feature request' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
} 