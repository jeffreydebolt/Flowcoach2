# FlowCoach BMAD Migration Plan

## Overview
Transform FlowCoach into a BMAD-METHOD expansion pack to leverage the full BMAD ecosystem while maintaining all current GTD and Slack integration capabilities.

## Benefits of BMAD Integration
- Access to BMAD's proven agent collaboration framework
- Automatic context preservation and handoffs between agents
- Expansion pack ecosystem for future enhancements
- Community-driven improvements and shared tools
- Better scalability for complex project management

## Phase 1: Setup BMAD Framework
1. Clone BMAD-METHOD repository
2. Install BMAD core dependencies
3. Understand BMAD agent structure and communication patterns
4. Set up development environment with BMAD tooling

## Phase 2: Create FlowCoach Expansion Pack Structure
```
expansion-packs/
└── flowcoach-gtd/
    ├── package.json
    ├── README.md
    ├── agents/
    │   ├── gtd-task-agent.js
    │   ├── gtd-planning-agent.js
    │   ├── gtd-review-agent.js
    │   └── slack-interface-agent.js
    ├── tools/
    │   ├── todoist-tool.js
    │   ├── calendar-tool.js
    │   └── slack-tool.js
    ├── contexts/
    │   └── gtd-context.js
    └── config/
        └── default.json
```

## Phase 3: Agent Migration Map

### Current FlowCoach → BMAD Agents
1. **TaskAgent** → **GTDTaskAgent**
   - Inherits from BMAD BaseAgent
   - Maintains all GTD formatting logic
   - Enhanced with BMAD context passing

2. **CalendarAgent** → **GTDSchedulingAgent**
   - Calendar blocking for deep work
   - Time estimation integration
   - Focus time optimization

3. **CommunicationAgent** → **SlackInterfaceAgent**
   - Handles Slack-specific formatting
   - Button/interactive component management
   - User preference tracking

4. **New: GTDPlanningAgent**
   - Leverages BMAD's planning capabilities
   - Project breakdown with GTD principles
   - Next action identification

5. **New: GTDReviewAgent**
   - Weekly review automation
   - Task completion analytics
   - Productivity insights

## Phase 4: Service → Tool Migration

### BMAD Tool Specifications
```javascript
// Example: todoist-tool.js
export const todoistTool = {
  name: 'todoist',
  description: 'Manage tasks in Todoist with GTD principles',
  
  operations: {
    createTask: {
      params: ['content', 'timeEstimate', 'project'],
      execute: async ({ content, timeEstimate, project }) => {
        // Port existing todoist_service logic
      }
    },
    
    getTasksByContext: {
      params: ['context'],
      execute: async ({ context }) => {
        // GTD context filtering
      }
    }
  }
};
```

## Phase 5: Slack Integration Adapter
- Create BMAD-Slack bridge for real-time messaging
- Maintain socket mode connection handling
- Port interactive component handlers
- Preserve user context across conversations

## Phase 6: Configuration Migration
```json
{
  "expansion": {
    "name": "flowcoach-gtd",
    "version": "2.0.0",
    "description": "GTD task management via Slack",
    "requiredTools": ["slack", "todoist", "calendar"],
    "agents": [
      "gtd-task-agent",
      "gtd-planning-agent",
      "gtd-review-agent",
      "slack-interface-agent"
    ]
  },
  "settings": {
    "gtd": {
      "contexts": ["@computer", "@phone", "@home", "@office"],
      "timeEstimates": ["2min", "10min", "30+min"],
      "reviewSchedule": "weekly"
    }
  }
}
```

## Migration Steps

### Week 1: Foundation
1. Set up BMAD development environment
2. Create expansion pack skeleton
3. Implement basic agent structure
4. Test BMAD agent communication

### Week 2: Core Migration
1. Port TaskAgent functionality
2. Migrate Todoist integration
3. Implement GTD context handling
4. Test task creation flow

### Week 3: Enhanced Features
1. Add planning and review agents
2. Implement project breakdown
3. Add analytics and insights
4. Calendar integration

### Week 4: Polish & Deploy
1. Slack adapter optimization
2. User preference migration
3. Testing and bug fixes
4. Documentation and deployment

## Testing Strategy
1. Unit tests for each BMAD agent
2. Integration tests for Slack ↔ BMAD flow
3. End-to-end GTD workflow tests
4. Performance benchmarking

## Rollback Plan
- Maintain current FlowCoach in parallel
- Feature flag for gradual migration
- Data export/import tools
- User notification strategy

## Success Metrics
- All current FlowCoach features working in BMAD
- Improved task planning with multi-agent collaboration
- Reduced context switching for users
- Access to BMAD expansion ecosystem

## Next Steps
1. Clone BMAD-METHOD repository
2. Review BMAD agent documentation
3. Create `flowcoach-gtd` expansion pack directory
4. Begin porting TaskAgent as proof of concept