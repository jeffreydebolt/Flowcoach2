# FlowCoach Improvements Summary

## Enhanced Natural Language Time Parsing

### What Was Added:
1. **Flexible Time Recognition**: The bot now recognizes time estimates in various formats:
   - "30 mins +" or "30 minutes plus" → [30+min]
   - "2 mins" or "2m" → [2min]
   - "45 minutes" → [30+min]
   - Parenthetical notation: "(5 min)" → [2min]
   - Dash notation: "- 30 mins" → [30+min]

2. **Time Extraction from Task Text**: Time estimates are automatically extracted from the task description and added as a prefix in square brackets, keeping them in the task title as requested.

### Examples:
- Input: "review email this morning - 30 mins +"
- Output: "[30+min] Review email this morning"

- Input: "email Aaron about cash flow questions 2 mins"
- Output: "[2min] Email Aaron about cash flow questions"

## Smart Project Detection

### What Was Added:
1. **Automatic Project Recognition**: When a task is estimated at 30+ minutes AND contains project-like language, the bot will ask if you want to break it down.

2. **Project Indicators**:
   - Action words: "build", "create", "develop", "implement", "establish"
   - Object words: "system", "forecast", "website", "strategy", "plan"
   - Scope words: "comprehensive", "full", "complete", "entire"

3. **Interactive Flow**: When a project is detected, you get options to:
   - Break it down into subtasks
   - Create it as a single task

### Example:
- Input: "build cash flow forecast for client a 30 mins plus"
- Bot response: "This sounds like it might be a project... Would you like me to break this down into smaller tasks?"

## Enhanced Task Breakdown

### What Was Added:
1. **GTD-Aligned Subtasks**: When breaking down projects, the bot generates 3-5 actionable subtasks following GTD principles.

2. **Logical Flow**: Subtasks follow a natural progression:
   - Research/planning tasks first
   - Implementation tasks in the middle
   - Review/finalization tasks at the end

3. **Time-Appropriate**: Each subtask is designed to take 2-30 minutes.

### Example Breakdown:
For "build cash flow forecast for client":
1. Review client's historical financial data
2. Create cash flow forecast template in Excel
3. Input revenue projections for next 12 months
4. Calculate expense projections based on historicals
5. Review forecast with team and finalize

## Technical Improvements

### Code Changes:
1. **Enhanced Time Parsing** (`task_agent.py`):
   - More comprehensive regex patterns
   - Extraction and cleaning of task text
   - Support for multiple time formats

2. **Project Detection** (`task_agent.py`):
   - Re-enabled and improved the `_is_likely_project` method
   - Added interactive project handling flow
   - Better OpenAI prompts for detection

3. **Improved Handlers** (`message_handlers.py`, `action_handlers.py`):
   - Added support for project detection responses
   - Enhanced breakdown suggestion handling
   - Fixed conversation state sharing between handlers

### Time Estimates in Task Titles:
As requested, time estimates are now stored in the task title using square bracket notation (e.g., "[30+min]") rather than as Todoist labels. This makes them visible at a glance and helps with prioritization.

## Usage Tips

1. **Natural Time Entry**: Just add time estimates naturally in your task:
   - "write report - 30 mins"
   - "quick email (2 min)"
   - "planning session 45 minutes"

2. **Project Detection**: For tasks over 30 minutes, be specific:
   - "build financial model" → Will trigger project prompt
   - "review financial model" → Won't trigger (review vs build)

3. **Skip Project Prompt**: If you don't want the project prompt, either:
   - Estimate under 30 minutes
   - Use non-project verbs like "review", "check", "update"

## Next Steps

To further improve the bot:
1. Add user preferences to control project detection sensitivity
2. Allow customization of time estimate brackets
3. Add support for recurring tasks with time estimates
4. Implement batch task creation with individual time estimates