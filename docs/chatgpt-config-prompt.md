# ChatGPT Prompt for Slack Wrapped Configuration

Use this prompt to help ChatGPT analyze your raw Slack data and generate the required configuration file.

---

## What You'll Provide to ChatGPT

ChatGPT needs **two inputs** from you:

### 1. Raw Slack Messages
Export or copy messages from your Slack channel. The tool supports these formats:

```
# Format 1: ISO timestamp
2025-03-15T14:23:00Z username: Message content here

# Format 2: US date format  
[3/15/2025 2:23 PM] username: Message content here

# Format 3: Simple format
username [14:23]: Message content here

# Format 4: Time first
14:23 username: Message content here

# Format 5: Date space format
2025-03-15 14:23 username: Message content here
```

### 2. Your Instructions (Team Structure & Context)
Tell ChatGPT about your team structure, display names, and any special context. Examples:

```
INSTRUCTIONS:
- Channel name: product-updates
- Year: 2025
- Teams:
  - Backend: david.shalom, bob.jones
  - Frontend: alice.smith, carol.white
  - DevOps: mike.chen
- Display names:
  - david.shalom = David Shalom
  - alice.smith = Alice Smith
- Context: This is our weekly product shipping channel
- Include gentle roasts: yes
```

---

## The ChatGPT Prompt

Copy and paste this entire prompt into ChatGPT, then add your **instructions** and **raw messages** at the end:

---

```
I need help preparing data for a "Slack Wrapped" video generator tool.

You will receive TWO inputs from me:
1. **INSTRUCTIONS** - My team structure, display names, and context
2. **RAW SLACK MESSAGES** - The actual messages from my Slack channel

IMPORTANT: Do NOT generate output files immediately! First analyze and ask me questions.

═══════════════════════════════════════════════════════════════════════════════
PHASE 1: ANALYZE & ASK QUESTIONS (Do this FIRST, before generating any files)
═══════════════════════════════════════════════════════════════════════════════

## STEP 1: Review the Messages
Read through ALL the messages and identify:
- What is this channel about? (product updates, team chat, announcements, etc.)
- What are the main topics/themes discussed?
- What's the overall tone? (formal, casual, celebratory, technical)
- Are there any major events or milestones mentioned?

## STEP 2: Extract Data Points
From the messages, extract:
- All unique usernames
- Date range (first and last message dates)
- Any team mentions or organizational hints
- Recurring topics or keywords
- Notable messages or achievements

## STEP 3: ASK CLARIFICATION QUESTIONS
Before generating any output, ASK ME about:

1. **Missing Usernames**: 
   "I found these usernames: [list]. Which ones need display name mappings?"
   
2. **Team Structure**: 
   "Based on the messages, it seems like [observations]. How are people organized into teams?"
   
3. **Channel Context**:
   "The channel appears to be about [topic]. Is this accurate? Any additional context?"
   
4. **Special Considerations**:
   "I noticed [observation]. Should I handle this in any special way?"
   
5. **Preferences**:
   "Do you want to include gentle roasts? How many top contributors to highlight?"

WAIT FOR MY ANSWERS before proceeding to Phase 2!

═══════════════════════════════════════════════════════════════════════════════
PHASE 2: GENERATE OUTPUT (Only after I answer your questions)
═══════════════════════════════════════════════════════════════════════════════

## STEP 4: Generate config.json
Create a config file in this EXACT format:

```json
{
  "channel": {
    "name": "channel-name",
    "description": "Brief description based on message content analysis",
    "year": 2025
  },
  "teams": [
    {
      "name": "Team Name",
      "members": ["username1", "username2"]
    }
  ],
  "userMappings": [
    {
      "slackUsername": "username1",
      "displayName": "Full Name",
      "team": "Team Name"
    }
  ],
  "preferences": {
    "includeRoasts": true,
    "topContributorsCount": 5
  },
  "context": {
    "channelPurpose": "What this channel is used for",
    "majorThemes": ["theme1", "theme2"],
    "keyMilestones": ["milestone1", "milestone2"],
    "tone": "casual/formal/celebratory"
  }
}
```

## STEP 5: Clean the Messages
Convert my raw messages into a consistent format:
- Use ISO timestamp: `2025-03-15T14:23:00Z username: Message`
- Remove system messages (joins, leaves, channel topic changes)
- Keep the original message content intact
- Remove any blank lines

## STEP 6: Generate Content Summary
Create a summary of the channel content:
- Main topics discussed
- Key achievements or milestones
- Notable quotes or messages
- Suggested "highlights" for the video

## OUTPUT FORMAT (Phase 2)
After I answer your questions, provide:
1. **config.json** - The complete configuration file with context
2. **messages.txt** - The cleaned messages file
3. **content-summary.md** - Summary of themes, milestones, and highlights
4. **Data Summary** - Stats (contributor count, date range, message count)

═══════════════════════════════════════════════════════════════════════════════

Remember: START with Phase 1 questions! Don't skip to generating files.

---

## MY INSTRUCTIONS:

[PASTE YOUR INSTRUCTIONS HERE]

---

## MY RAW SLACK MESSAGES:

[PASTE YOUR MESSAGES HERE]
```

---

## Example Instructions Format

Here are different ways you can provide your instructions:

### Option A: Structured List
```
INSTRUCTIONS:
- Channel: product-updates
- Year: 2025
- Teams:
  - Backend: david.shalom, bob.jones, mike.chen
  - Frontend: alice.smith, carol.white
  - QA: jane.doe
- Display names:
  - david.shalom = David Shalom (Team Lead)
  - alice.smith = Alice Smith
  - bob.jones = Bob Jones
  - carol.white = Carol White
  - mike.chen = Mike Chen
  - jane.doe = Jane Doe
- Context: Weekly product shipping updates and announcements
- Include roasts: yes
- Top contributors to show: 5
```

### Option B: Free-form Description
```
INSTRUCTIONS:
This is our product-updates channel from 2025.

We have two teams:
- The Backend team includes David Shalom (david.shalom), Bob Jones (bob.jones), and Mike Chen (mike.chen)
- The Frontend team includes Alice Smith (alice.smith) and Carol White (carol.white)

David is the team lead. We want to include gentle roasts in the video and show the top 5 contributors.
```

### Option C: Minimal (ChatGPT will ask questions)
```
INSTRUCTIONS:
- Channel: product-updates
- Year: 2025
- I'll answer questions about teams and names
```

---

## After ChatGPT Generates the Files

### Save the Output

1. **Save the config** as `my-config.json`
2. **Save the cleaned messages** as `my-messages.txt`

### Test with Slack Wrapped

```bash
# Validate your files
python3 -m slack_wrapped validate \
  --data my-messages.txt \
  --config my-config.json

# Test the full pipeline
python3 test_my_data.py \
  --data my-messages.txt \
  --config my-config.json

# Generate video data (requires OPENAI_API_KEY)
python3 -m slack_wrapped generate \
  --data my-messages.txt \
  --config my-config.json \
  --output output/
```

---

## Troubleshooting

### "No messages parsed" error
- Check that your message format matches one of the supported formats
- Ensure there's no extra whitespace or formatting issues
- Ask ChatGPT to re-format the messages

### "Config validation failed" error
- Ensure all usernames in `userMappings` match the usernames in your messages
- Check that `teams` and `userMappings` reference the same team names
- Verify the JSON syntax is valid

### Username not found in output
- Check for username variations (e.g., `david.s` vs `david.shalom`)
- Add all variations to `userMappings`
- Ask ChatGPT to list all unique usernames it found

### Missing team assignments
- Ensure every username in `userMappings` has a matching `team` field
- The team name must match exactly with a team in the `teams` array
