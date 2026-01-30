"""FastAPI web server for Slack Wrapped interactive setup.

Provides a web-based UI for the interactive setup wizard.
"""

import json
import logging
import os
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .message_analyzer import MessageAnalyzer, AnalysisResult
from .config_generator import ConfigGenerator, generate_config
from .parser import SlackParser, ParserError
from .llm_client import LLMClient, create_llm_client, LLMError
from .file_extractor import extract_text_from_file, FileExtractionError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set log levels for our modules
logging.getLogger('slack_wrapped').setLevel(logging.DEBUG)
logging.getLogger('slack_wrapped.parser').setLevel(logging.DEBUG)
logging.getLogger('slack_wrapped.message_analyzer').setLevel(logging.DEBUG)
logging.getLogger('slack_wrapped.file_extractor').setLevel(logging.DEBUG)

# Create FastAPI app
app = FastAPI(
    title="Slack Wrapped Setup",
    description="Interactive setup wizard for Slack Wrapped video generation",
    version="1.0.0",
)

# Store analysis results in memory (for single-user local use)
_analysis_store: dict[str, AnalysisResult] = {}
_messages_store: dict[str, str] = {}


# Inline HTML template (no external files needed)
SETUP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slack Wrapped - Setup</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .step { display: none; }
        .step.active { display: block; }
        .fade-in { animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    </style>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-3xl">
        <!-- Header -->
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold text-cyan-400 mb-2">Slack Wrapped</h1>
            <p class="text-gray-400">Interactive Setup Wizard</p>
        </div>

        <!-- Progress Bar -->
        <div class="mb-8">
            <div class="flex justify-between mb-2">
                <span id="step-label" class="text-sm text-gray-400">Step 1 of 5</span>
                <span id="step-name" class="text-sm text-cyan-400">Upload Messages</span>
            </div>
            <div class="w-full bg-gray-700 rounded-full h-2">
                <div id="progress-bar" class="bg-cyan-500 h-2 rounded-full transition-all duration-300" style="width: 20%"></div>
            </div>
        </div>

        <!-- Step 1: Upload -->
        <div id="step-1" class="step active fade-in bg-gray-800 rounded-lg p-6 shadow-lg">
            <h2 class="text-xl font-semibold mb-4">Upload Your Slack Messages</h2>
            <p class="text-gray-400 mb-6">
                Paste your raw Slack messages or upload a text file.
                The tool supports multiple formats.
            </p>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-2">Message File</label>
                <input type="file" id="file-input" accept=".txt,.log,.md,.markdown,.pdf" 
                    class="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 
                           file:rounded file:border-0 file:text-sm file:font-semibold 
                           file:bg-cyan-600 file:text-white hover:file:bg-cyan-700 cursor-pointer">
                <p class="text-xs text-gray-500 mt-1">Supports: TXT, MD, PDF, LOG files</p>
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-2">Or paste messages directly</label>
                <textarea id="messages-text" rows="10" 
                    class="w-full bg-gray-700 rounded p-3 text-sm font-mono"
                    placeholder="2025-01-15T09:30:00Z david.shalom: Good morning team!
2025-01-15T09:32:00Z alice.smith: Morning David!
..."></textarea>
            </div>
            
            <div id="upload-error" class="text-red-400 text-sm mb-4 hidden"></div>
            
            <button onclick="analyzeMessages()" 
                class="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-semibold py-3 px-6 rounded transition">
                Analyze Messages
            </button>
            
            <div id="loading" class="hidden mt-4 text-center">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-cyan-500 border-t-transparent"></div>
                <p class="mt-2 text-gray-400">Analyzing messages with AI...</p>
            </div>
        </div>

        <!-- Step 2: Analysis Results -->
        <div id="step-2" class="step fade-in bg-gray-800 rounded-lg p-6 shadow-lg">
            <h2 class="text-xl font-semibold mb-4">Analysis Results</h2>
            
            <div id="analysis-summary" class="mb-6">
                <!-- Filled by JavaScript -->
            </div>
            
            <div class="flex gap-4">
                <button onclick="goToStep(1)" class="flex-1 bg-gray-600 hover:bg-gray-700 py-2 px-4 rounded">
                    Back
                </button>
                <button onclick="goToStep(3)" class="flex-1 bg-cyan-600 hover:bg-cyan-700 py-2 px-4 rounded">
                    Continue
                </button>
            </div>
        </div>

        <!-- Step 3: Basic Info -->
        <div id="step-3" class="step fade-in bg-gray-800 rounded-lg p-6 shadow-lg">
            <h2 class="text-xl font-semibold mb-4">Channel Information</h2>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-1">Channel Name *</label>
                    <input type="text" id="channel-name" 
                        class="w-full bg-gray-700 rounded p-2" required>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-1">Year *</label>
                    <input type="number" id="year" 
                        class="w-full bg-gray-700 rounded p-2" required>
                </div>
                
                <div>
                    <label class="block text-sm font-medium mb-1">Description</label>
                    <input type="text" id="channel-description" 
                        class="w-full bg-gray-700 rounded p-2">
                </div>
            </div>
            
            <div class="flex gap-4 mt-6">
                <button onclick="goToStep(2)" class="flex-1 bg-gray-600 hover:bg-gray-700 py-2 px-4 rounded">
                    Back
                </button>
                <button onclick="goToStep(4)" class="flex-1 bg-cyan-600 hover:bg-cyan-700 py-2 px-4 rounded">
                    Continue
                </button>
            </div>
        </div>

        <!-- Step 4: User Mappings -->
        <div id="step-4" class="step fade-in bg-gray-800 rounded-lg p-6 shadow-lg">
            <h2 class="text-xl font-semibold mb-4">User Display Names</h2>
            <p class="text-gray-400 mb-4">Edit display names for each contributor.</p>
            
            <div id="user-mappings" class="space-y-2 max-h-80 overflow-y-auto">
                <!-- Filled by JavaScript -->
            </div>
            
            <div class="flex gap-4 mt-6">
                <button onclick="goToStep(3)" class="flex-1 bg-gray-600 hover:bg-gray-700 py-2 px-4 rounded">
                    Back
                </button>
                <button onclick="goToStep(5)" class="flex-1 bg-cyan-600 hover:bg-cyan-700 py-2 px-4 rounded">
                    Continue
                </button>
            </div>
        </div>

        <!-- Step 5: Review & Generate -->
        <div id="step-5" class="step fade-in bg-gray-800 rounded-lg p-6 shadow-lg">
            <h2 class="text-xl font-semibold mb-4">Review Configuration</h2>
            
            <div class="mb-4">
                <label class="flex items-center gap-2">
                    <input type="checkbox" id="include-roasts" checked class="rounded">
                    <span>Include gentle roasts and playful humor</span>
                </label>
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Top Contributors to Highlight</label>
                <input type="number" id="top-count" value="5" min="1" max="20"
                    class="w-24 bg-gray-700 rounded p-2">
            </div>
            
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Generated Config (editable)</label>
                <textarea id="config-json" rows="12" 
                    class="w-full bg-gray-700 rounded p-3 text-sm font-mono"></textarea>
            </div>
            
            <div id="generate-error" class="text-red-400 text-sm mb-4 hidden"></div>
            
            <div class="flex gap-4">
                <button onclick="goToStep(4)" class="flex-1 bg-gray-600 hover:bg-gray-700 py-2 px-4 rounded">
                    Back
                </button>
                <button onclick="saveConfig()" class="flex-1 bg-green-600 hover:bg-green-700 py-2 px-4 rounded font-semibold">
                    Save & Continue
                </button>
            </div>
        </div>

        <!-- Success -->
        <div id="step-success" class="step fade-in bg-gray-800 rounded-lg p-6 shadow-lg text-center">
            <div class="text-6xl mb-4">🎉</div>
            <h2 class="text-2xl font-semibold mb-4 text-green-400">Setup Complete!</h2>
            <p class="text-gray-400 mb-6">Your configuration has been saved.</p>
            
            <div class="bg-gray-700 rounded p-4 mb-6 text-left">
                <p class="text-sm font-mono">Config saved to: <span id="config-path" class="text-cyan-400"></span></p>
            </div>
            
            <div class="space-y-2">
                <p class="text-sm text-gray-400">Next steps:</p>
                <code class="block bg-gray-700 rounded p-3 text-sm text-left">
python -m slack_wrapped generate \\
  --data messages.txt \\
  --config <span id="config-filename">config.json</span>
                </code>
            </div>
        </div>
    </div>

    <script>
        // Global state
        let currentStep = 1;
        let analysisData = null;
        let sessionId = null;

        const stepNames = [
            'Upload Messages',
            'Analysis Results', 
            'Channel Information',
            'User Mappings',
            'Review & Generate'
        ];

        function goToStep(step) {
            document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
            document.getElementById(`step-${step}`).classList.add('active');
            currentStep = step;
            
            // Update progress
            document.getElementById('progress-bar').style.width = `${step * 20}%`;
            document.getElementById('step-label').textContent = `Step ${step} of 5`;
            document.getElementById('step-name').textContent = stepNames[step - 1];
            
            // Pre-fill step data
            if (step === 5) {
                updateConfigPreview();
            }
        }

        async function analyzeMessages() {
            const fileInput = document.getElementById('file-input');
            const textInput = document.getElementById('messages-text');
            const loading = document.getElementById('loading');
            const errorEl = document.getElementById('upload-error');
            
            let messages = textInput.value.trim();
            let fileData = null;
            let filename = null;
            
            // Read file if uploaded
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                filename = file.name;
                
                // For PDF files, send as base64
                if (filename.toLowerCase().endsWith('.pdf')) {
                    const buffer = await file.arrayBuffer();
                    fileData = btoa(String.fromCharCode(...new Uint8Array(buffer)));
                } else {
                    // For text files, read as text
                    messages = await file.text();
                }
            }
            
            if (!messages && !fileData) {
                errorEl.textContent = 'Please upload a file or paste messages';
                errorEl.classList.remove('hidden');
                return;
            }
            
            errorEl.classList.add('hidden');
            loading.classList.remove('hidden');
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        messages: messages || null,
                        file_data: fileData,
                        filename: filename
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Analysis failed');
                }
                
                analysisData = data;
                sessionId = data.session_id;
                
                // Show analysis summary
                showAnalysisSummary(data);
                
                // Pre-fill form fields
                document.getElementById('channel-name').value = data.channel_analysis?.likely_name || '';
                document.getElementById('year').value = data.year || new Date().getFullYear();
                document.getElementById('channel-description').value = data.channel_analysis?.purpose || '';
                
                // Build user mappings
                buildUserMappings(data.user_suggestions || []);
                
                goToStep(2);
                
            } catch (error) {
                errorEl.textContent = error.message;
                errorEl.classList.remove('hidden');
            } finally {
                loading.classList.add('hidden');
            }
        }

        function showAnalysisSummary(data) {
            const container = document.getElementById('analysis-summary');
            const ca = data.channel_analysis || {};
            
            let html = `
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div class="bg-gray-700 rounded p-3">
                        <div class="text-2xl font-bold text-cyan-400">${data.total_messages || 0}</div>
                        <div class="text-sm text-gray-400">Messages</div>
                    </div>
                    <div class="bg-gray-700 rounded p-3">
                        <div class="text-2xl font-bold text-cyan-400">${(data.usernames || []).length}</div>
                        <div class="text-sm text-gray-400">Contributors</div>
                    </div>
                </div>
            `;
            
            if (ca.purpose) {
                html += `<p class="mb-2"><strong>Purpose:</strong> ${ca.purpose}</p>`;
            }
            if (ca.tone) {
                html += `<p class="mb-2"><strong>Tone:</strong> ${ca.tone}</p>`;
            }
            if (ca.main_topics && ca.main_topics.length > 0) {
                html += `<p class="mb-2"><strong>Topics:</strong> ${ca.main_topics.join(', ')}</p>`;
            }
            
            container.innerHTML = html;
        }

        function buildUserMappings(users) {
            const container = document.getElementById('user-mappings');
            
            container.innerHTML = users.map((user, i) => `
                <div class="flex items-center gap-2 bg-gray-700 rounded p-2">
                    <span class="text-gray-400 w-40 truncate">${user.username}</span>
                    <span class="text-gray-500">→</span>
                    <input type="text" 
                        id="user-${i}" 
                        data-username="${user.username}"
                        value="${user.suggested_name}"
                        class="flex-1 bg-gray-600 rounded px-2 py-1">
                    <span class="text-gray-500 text-sm">(${user.message_count} msgs)</span>
                </div>
            `).join('');
        }

        function collectUserMappings() {
            const mappings = [];
            document.querySelectorAll('#user-mappings input').forEach(input => {
                mappings.push({
                    slack_username: input.dataset.username,
                    display_name: input.value
                });
            });
            return mappings;
        }

        function updateConfigPreview() {
            const config = {
                channel: {
                    name: document.getElementById('channel-name').value,
                    year: parseInt(document.getElementById('year').value),
                    description: document.getElementById('channel-description').value
                },
                teams: analysisData?.team_suggestions?.map(t => ({
                    name: t.name,
                    members: t.members
                })) || [],
                userMappings: collectUserMappings().map(m => ({
                    slackUsername: m.slack_username,
                    displayName: m.display_name,
                    team: ''
                })),
                preferences: {
                    includeRoasts: document.getElementById('include-roasts').checked,
                    topContributorsCount: parseInt(document.getElementById('top-count').value)
                },
                context: {
                    channelPurpose: analysisData?.channel_analysis?.purpose || '',
                    majorThemes: analysisData?.channel_analysis?.main_topics || [],
                    keyMilestones: analysisData?.channel_analysis?.key_milestones || [],
                    tone: analysisData?.channel_analysis?.tone || ''
                }
            };
            
            document.getElementById('config-json').value = JSON.stringify(config, null, 2);
        }

        async function saveConfig() {
            const configJson = document.getElementById('config-json').value;
            const errorEl = document.getElementById('generate-error');
            
            try {
                const config = JSON.parse(configJson);
                
                const response = await fetch('/api/save-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        config,
                        session_id: sessionId
                    })
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.detail || 'Save failed');
                }
                
                // Show success
                document.getElementById('config-path').textContent = data.path;
                document.getElementById('config-filename').textContent = data.filename;
                
                document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
                document.getElementById('step-success').classList.add('active');
                document.getElementById('progress-bar').style.width = '100%';
                
            } catch (error) {
                errorEl.textContent = error.message;
                errorEl.classList.remove('hidden');
            }
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the setup wizard page."""
    return SETUP_HTML


@app.post("/api/analyze")
async def analyze_messages(request: Request):
    """
    Analyze uploaded messages and return insights.
    
    Expects JSON body with:
    - messages: string of raw Slack messages (for text files)
    - file_data: base64 encoded file content (for PDF files)
    - filename: original filename (for format detection)
    """
    try:
        data = await request.json()
        messages_text = data.get("messages", "")
        file_data = data.get("file_data")
        filename = data.get("filename", "")
        
        logger.info(f"Analyze request received: filename={filename}, has_file_data={bool(file_data)}, text_length={len(messages_text) if messages_text else 0}")
        
        # Handle file upload (PDF or other binary)
        if file_data and filename:
            import base64
            logger.info(f"Processing file upload: {filename}")
            try:
                file_bytes = base64.b64decode(file_data)
                logger.info(f"Decoded file: {len(file_bytes)} bytes")
                messages_text = extract_text_from_file(
                    file_content=file_bytes,
                    filename=filename,
                )
                logger.info(f"Extracted text: {len(messages_text)} characters")
            except FileExtractionError as e:
                logger.error(f"File extraction error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.exception("File extraction failed")
                raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {e}")
        
        if not messages_text:
            logger.warning("No messages provided in request")
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Log sample of input for debugging
        lines = messages_text.strip().split('\n')
        logger.info(f"Input has {len(lines)} lines")
        if lines:
            logger.debug(f"First 3 lines sample:")
            for i, line in enumerate(lines[:3]):
                logger.debug(f"  Line {i+1}: {line[:100]}")
        
        # Parse messages with debug mode
        parser = SlackParser()
        try:
            messages = parser.parse(messages_text, debug=True)
            logger.info(f"Successfully parsed {len(messages)} messages")
        except ParserError as e:
            logger.error(f"Parser error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Check for OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Return basic analysis without LLM
            return _basic_analysis(messages)
        
        # Create LLM client and analyzer
        try:
            llm = create_llm_client(api_key=api_key)
            analyzer = MessageAnalyzer(llm)
            result = analyzer.analyze(messages)
        except LLMError as e:
            logger.warning(f"LLM analysis failed: {e}")
            return _basic_analysis(messages)
        
        # Generate session ID and store result
        import uuid
        session_id = str(uuid.uuid4())
        _analysis_store[session_id] = result
        _messages_store[session_id] = messages_text
        
        # Convert to JSON-serializable dict
        return {
            "session_id": session_id,
            "total_messages": result.total_messages,
            "date_range": {
                "start": result.date_range[0].isoformat() if result.date_range[0] else None,
                "end": result.date_range[1].isoformat() if result.date_range[1] else None,
            },
            "year": result.year,
            "usernames": result.usernames,
            "message_counts": result.message_counts,
            "channel_analysis": {
                "likely_name": result.channel_analysis.likely_name,
                "purpose": result.channel_analysis.purpose,
                "tone": result.channel_analysis.tone,
                "main_topics": result.channel_analysis.main_topics,
                "key_milestones": result.channel_analysis.key_milestones,
                "notable_patterns": result.channel_analysis.notable_patterns,
            },
            "team_suggestions": [
                {"name": t.name, "members": t.members, "reasoning": t.reasoning}
                for t in result.team_suggestions
            ],
            "user_suggestions": [
                {
                    "username": u.username,
                    "suggested_name": u.suggested_name,
                    "message_count": u.message_count,
                    "confidence": u.confidence,
                }
                for u in result.user_suggestions
            ],
            "highlights": [
                {
                    "type": h.type,
                    "description": h.description,
                    "quote": h.quote,
                    "contributor": h.contributor,
                }
                for h in result.highlights
            ],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


def _basic_analysis(messages):
    """Return basic analysis without LLM."""
    from collections import Counter
    
    usernames = set()
    message_counts = Counter()
    min_date = max_date = None
    
    for msg in messages:
        usernames.add(msg.username)
        message_counts[msg.username] += 1
        if min_date is None or msg.timestamp < min_date:
            min_date = msg.timestamp
        if max_date is None or msg.timestamp > max_date:
            max_date = msg.timestamp
    
    sorted_users = sorted(usernames)
    
    return {
        "session_id": None,
        "total_messages": len(messages),
        "date_range": {
            "start": min_date.isoformat() if min_date else None,
            "end": max_date.isoformat() if max_date else None,
        },
        "year": min_date.year if min_date else 2025,
        "usernames": sorted_users,
        "message_counts": dict(message_counts),
        "channel_analysis": {
            "likely_name": "",
            "purpose": "",
            "tone": "",
            "main_topics": [],
            "key_milestones": [],
            "notable_patterns": [],
        },
        "team_suggestions": [],
        "user_suggestions": [
            {
                "username": u,
                "suggested_name": " ".join(p.capitalize() for p in u.replace("_", ".").split(".")),
                "message_count": message_counts[u],
                "confidence": "low",
            }
            for u in sorted_users
        ],
        "highlights": [],
    }


@app.post("/api/save-config")
async def save_config_endpoint(request: Request):
    """
    Save the generated configuration.
    
    Expects JSON body with:
    - config: configuration dictionary
    - session_id: optional session ID
    """
    try:
        data = await request.json()
        config = data.get("config")
        session_id = data.get("session_id")
        
        if not config:
            raise HTTPException(status_code=400, detail="No config provided")
        
        # Validate required fields
        if not config.get("channel", {}).get("name"):
            raise HTTPException(status_code=400, detail="Channel name is required")
        if not config.get("channel", {}).get("year"):
            raise HTTPException(status_code=400, detail="Year is required")
        
        # Generate output path
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        channel_name = config["channel"]["name"]
        filename = f"config-{channel_name}.json"
        output_path = output_dir / filename
        
        # Save config
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)
        
        # Save messages if we have them
        if session_id and session_id in _messages_store:
            messages_path = output_dir / f"messages-{channel_name}.txt"
            with open(messages_path, "w") as f:
                f.write(_messages_store[session_id])
        
        return {
            "success": True,
            "path": str(output_path.absolute()),
            "filename": filename,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Save failed")
        raise HTTPException(status_code=500, detail=str(e))


def run_server(
    data_file: Optional[str] = None,
    port: int = 8080,
    open_browser: bool = True,
):
    """
    Run the web server.
    
    Args:
        data_file: Optional path to pre-load messages from
        port: Port to run on
        open_browser: Whether to open browser automatically
    """
    import uvicorn
    
    # Pre-load data if provided
    if data_file:
        path = Path(data_file)
        if path.exists():
            with open(path) as f:
                _messages_store["preloaded"] = f.read()
    
    # Open browser
    if open_browser:
        import threading
        def open_browser_delayed():
            import time
            time.sleep(1)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=open_browser_delayed, daemon=True).start()
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run_server()
