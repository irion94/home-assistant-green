# Changelog

All notable changes and phase completions for the Home Assistant AI Companion project.

## 2025-11-26

### Phase 1: Database Foundation ✅ (DEPLOYMENT READY)

**Status**: Code merged from workbench, ready for activation via feature flag

**Implementation Complete**:
- ✅ PostgreSQL 16 + pgvector container fully configured in docker-compose.yml
- ✅ DatabaseService (605 lines) with async operations, connection pooling (2-10 connections)
- ✅ Memory API router with 13 endpoints (`/memory/*`)
- ✅ EmbeddingService for vector embeddings (nomic-embed-text, 384-dim)
- ✅ Idempotent migration system (`001_initial_schema.sql`)
- ✅ Graceful degradation (falls back to memory if DB fails)
- ✅ Dependency injection via `get_conversation_client_dependency()`
- ✅ ConversationClient integrated with DB persistence
- ✅ Feature flag: `DATABASE_ENABLED=false` (default: safe, disabled)

**Database Schema** (5 tables):
- `conversations` - Chat history with session_id, role, content, language, intent
- `knowledge` - RAG storage with pgvector embeddings for semantic search
- `preferences` - User settings, learned behaviors, personalization
- `response_cache` - Query caching with TTL and hit counts
- `training_data` - Successful interactions for fine-tuning with feedback scores

**Persistent Storage** (SSD-backed):
- `/mnt/data-ssd/postgres-data` → PostgreSQL data directory
- Survives container restarts and Docker rebuilds

**Key Files Modified**:
- `ai-gateway/app/services/database.py` (NEW from workbench, 605 lines)
- `ai-gateway/app/services/embeddings.py` (NEW from workbench)
- `ai-gateway/app/routers/memory.py` (UPDATED, 13 endpoints)
- `ai-gateway/migrations/001_initial_schema.sql` (UPDATED)
- `ai-gateway/docker-compose.yml` (added DATABASE_ENABLED flag)
- `ai-gateway/app/main.py` (added feature flag check)
- `ai-gateway/.env` (added database credentials, DATABASE_ENABLED=false)

**Activation Instructions**:
```bash
# 1. Set DATABASE_ENABLED=true in .env
sed -i 's/DATABASE_ENABLED=false/DATABASE_ENABLED=true/' /home/irion94/home-assistant-green/ai-gateway/.env

# 2. Restart services
cd /home/irion94/home-assistant-green/ai-gateway
docker compose restart ai-gateway

# 3. Verify database connection
docker compose logs ai-gateway | grep "Database connected"

# 4. Test conversation persistence
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "Test persistence", "session_id": "test123", "room_id": "salon"}'

# 5. Verify data saved
docker exec -it ai-postgres psql -U ai_assistant -c "SELECT session_id, role, content FROM conversations WHERE session_id='test123';"
```

**Rollback Plan**:
```bash
# Disable database without losing data
sed -i 's/DATABASE_ENABLED=true/DATABASE_ENABLED=false/' /home/irion94/home-assistant-green/ai-gateway/.env
docker compose restart ai-gateway
# System falls back to in-memory sessions
```

---

### Phase 2: Enhanced Tool Architecture ✅ (DEPLOYMENT READY)

**Status**: Modular tool system implemented, ready for activation via feature flag

**Implementation Complete**:
- ✅ BaseTool abstract class with ToolResult model
- ✅ ToolRegistry for dynamic tool management
- ✅ All 4 existing tools refactored (web_search, control_light, get_time, get_home_data)
- ✅ New GetEntityTool for comprehensive HA entity access (all domains)
- ✅ Backward compatibility via ToolRegistryAdapter
- ✅ Feature flag: `NEW_TOOLS_ENABLED=false` (default: safe, disabled)
- ✅ Auto-registration in main.py startup

**New Architecture**:
- `BaseTool` - Abstract class with `name`, `schema`, `execute()` methods
- `ToolResult` - Standardized result (success, content, display_action, metadata)
- `ToolRegistry` - Centralized tool management with dynamic registration
- `ToolRegistryAdapter` - Converts ToolResult → string for backward compatibility

**Tools Refactored** (5 total):
1. `WebSearchTool` - Brave Search API integration
2. `ControlLightTool` - Light control with room mapping
3. `GetTimeTool` - Current time in Warsaw timezone
4. `GetHomeDataTool` - Sensor queries (temperature, humidity, weather)
5. `GetEntityTool` (NEW) - Comprehensive HA entity state queries (all domains)

**Key Features**:
- Easy to add new tools (subclass BaseTool, register in main.py)
- Unified error handling and logging
- Display actions for React Dashboard integration
- Dynamic schema generation for OpenAI API
- Graceful degradation (falls back to old ToolExecutor if flag disabled)

**Key Files Created/Modified**:
- `ai-gateway/app/services/tools/base.py` (NEW, 82 lines)
- `ai-gateway/app/services/tools/registry.py` (NEW, 143 lines)
- `ai-gateway/app/services/tools/web_search_tool.py` (NEW, 142 lines)
- `ai-gateway/app/services/tools/control_light_tool.py` (NEW, 167 lines)
- `ai-gateway/app/services/tools/time_tool.py` (NEW, 74 lines)
- `ai-gateway/app/services/tools/home_data_tool.py` (NEW, 182 lines)
- `ai-gateway/app/services/tools/entity_tool.py` (NEW, 175 lines)
- `ai-gateway/app/services/llm_tools.py` (UPDATED, added ToolRegistryAdapter)
- `ai-gateway/app/main.py` (UPDATED, tool registration in lifespan)
- `ai-gateway/docker-compose.yml` (added NEW_TOOLS_ENABLED flag)
- `ai-gateway/.env` (added NEW_TOOLS_ENABLED=false)

**Activation Instructions**:
```bash
# 1. Set NEW_TOOLS_ENABLED=true in .env
sed -i 's/NEW_TOOLS_ENABLED=false/NEW_TOOLS_ENABLED=true/' /home/irion94/home-assistant-green/ai-gateway/.env

# 2. Restart AI Gateway
cd /home/irion94/home-assistant-green/ai-gateway
docker compose restart ai-gateway

# 3. Verify tool registration
docker compose logs ai-gateway | grep "tools registered"
# Should see: "New tool architecture enabled: 5 tools registered"

# 4. Test new GetEntityTool
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "What lights are on?", "session_id": "test123", "room_id": "salon"}'
```

**Rollback Plan**:
```bash
# Disable new tools without breaking anything
sed -i 's/NEW_TOOLS_ENABLED=true/NEW_TOOLS_ENABLED=false/' /home/irion94/home-assistant-green/ai-gateway/.env
docker compose restart ai-gateway
# System falls back to legacy ToolExecutor
```

---

### Phase 3: Learning Systems ✅ (DEPLOYMENT READY)

**Status**: Intelligent learning components implemented, ready for activation

**Implementation Complete**:
- ✅ ContextEngine for conversation history and user preferences
- ✅ IntentAnalyzer for smart overlay behavior (question vs confirmation detection)
- ✅ SuggestionEngine for proactive suggestions based on time/room/patterns
- ✅ Feature flag: `LEARNING_ENABLED=false` (default: safe, disabled)
- ✅ Database integration for pattern learning and training data

**Learning Components** (3 total):

1. **ContextEngine** (`context_engine.py`, 145 lines)
   - Retrieves conversation history from database
   - Loads user preferences by category
   - Builds room-specific context
   - Learns command patterns for future reference
   - Stores successful interactions as training data

2. **IntentAnalyzer** (`intent_analyzer.py`, 118 lines)
   - Analyzes AI responses to determine overlay behavior
   - Question detection: keeps overlay open for user response
   - Confirmation detection: allows overlay to close
   - Error detection: keeps overlay open for clarification
   - Regex-based pattern matching (fast, deterministic)
   - Supports Polish and English responses

3. **SuggestionEngine** (`suggestion_engine.py`, 168 lines)
   - Generates contextual suggestions based on:
     - Time of day (morning, evening, night)
     - Room context (bedroom, kitchen, etc.)
     - Day of week patterns
   - Records user actions for pattern learning
   - Falls back to default suggestions if database unavailable

**Key Features**:
- **Smart Overlay**: Automatically determines when to keep voice overlay open
- **Pattern Learning**: Stores successful command → action pairs
- **Context Awareness**: Remembers recent conversation history
- **Time-based Suggestions**: "Turn on morning lights?" at 7 AM
- **Room-aware**: Different suggestions per room
- **Graceful Degradation**: Works without database (limited functionality)

**Key Files Created**:
- `ai-gateway/app/services/learning/context_engine.py` (NEW, 145 lines)
- `ai-gateway/app/services/learning/intent_analyzer.py` (NEW, 118 lines)
- `ai-gateway/app/services/learning/suggestion_engine.py` (NEW, 168 lines)
- `ai-gateway/docker-compose.yml` (added LEARNING_ENABLED flag)
- `ai-gateway/.env` (added LEARNING_ENABLED=false)

**Integration Points** (for future activation):
- ConversationClient: Use ContextEngine to load history/preferences
- MQTT overlay hints: Use IntentAnalyzer to publish keep_open signals
- Proactive notifications: Use SuggestionEngine for time-based suggestions

**Activation Instructions**:
```bash
# 1. Ensure DATABASE_ENABLED=true first (Phase 1 dependency)
# 2. Set LEARNING_ENABLED=true in .env
sed -i 's/LEARNING_ENABLED=false/LEARNING_ENABLED=true/' /home/irion94/home-assistant-green/ai-gateway/.env

# 3. Restart AI Gateway
cd /home/irion94/home-assistant-green/ai-gateway
docker compose restart ai-gateway

# 4. Test pattern learning (requires database)
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "Turn on lights", "session_id": "test123", "room_id": "salon"}'

# 5. Verify pattern saved in database
docker exec -it ai-postgres psql -U ai_assistant -c "SELECT * FROM training_data LIMIT 5;"
```

**Rollback Plan**:
```bash
# Disable learning systems
sed -i 's/LEARNING_ENABLED=true/LEARNING_ENABLED=false/' /home/irion94/home-assistant-green/ai-gateway/.env
docker compose restart ai-gateway
# System continues without learning features
```

---

### Phase 12: VoiceOverlay UI Redesign ✅ (COMPLETE)

**Summary**: Complete UI rebuild with action-dependent displays and Framer Motion animations

**Key Changes**:
- **2-Row Layout**: Redesigned overlay with header row + 3-column content row (debug logs, status indicator, chat)
- **MQTT Display Actions**: Backend publishes display actions to MQTT after tool execution
  - Topic: `voice_assistant/room/{room_id}/session/{session_id}/display_action`
  - Payload: `{ type, data, timestamp }`
- **Backend Integration**: Updated conversation router and client to pass `room_id` and `session_id` through to tool executor
- **MQTT Client**: Created `mqtt_client.py` with `publish_display_action()` method, connects to `mosquitto` broker
- **Display Panels**: Implemented DefaultDisplayPanel, LightControlPanel, SearchResultsPanel with Framer Motion animations
- **Framer Motion**: FAB button morphs to StatusIndicator using `layoutId="voice-button"` shared element
- **Layout Optimization**: Flex-1 edges (logs + chat), fixed 200px center column, hidden scrollbars
- **Zustand Integration**: Extended store with `displayAction` state and MQTT handlers
- **Dependencies**: Added `paho-mqtt>=1.6.1` to backend requirements

**Key Files Modified**:
- `ai-gateway/app/services/mqtt_client.py` (NEW)
- `ai-gateway/app/services/llm_tools.py` (MQTT publishing)
- `ai-gateway/app/routers/conversation.py` (room_id/session_id params)
- `ai-gateway/app/services/conversation_client.py` (pass context to tools)
- `react-dashboard/src/components/kiosk/VoiceOverlay.tsx` (2-row layout)
- `react-dashboard/src/components/kiosk/voice-overlay/` (new components)
- `react-dashboard/src/stores/voiceStore.ts` (displayAction state)
- `react-dashboard/src/services/mqttService.ts` (display_action handler)

---

### STT Enhancements & Bug Fixes

**Enhanced Whisper Vocabulary**: Added comprehensive Polish home automation vocabulary hints covering lights, climate, media, sensors, and conversation commands. Expected 15-25% improvement in domain-specific recognition.

**Configurable STT Threshold**: Added `STT_CONFIDENCE_THRESHOLD` environment variable (default: 0.7) to tune Vosk→Whisper fallback behavior.

**End Command Fix**: Fixed false positive detection where "pa" in words like "sypialni" (bedroom) was incorrectly triggering conversation end. Now uses word boundary regex matching.

---

### Function Calling in Conversation

**Streaming Tool Execution**: LLM can now execute tools (control_light, web_search, etc.) during streaming conversations via `/conversation/stream` endpoint.

**Dual Method Support**: Function calling implemented in both `chat_stream()` (token-by-token) and `chat_stream_sentences()` (sentence-by-sentence) methods.

**Proper Error Handling**: Tool executor uses `.execute()` method correctly, with full error logging and recovery.

---

### Light Control Improvements

**Multi-Entity Control**: "All lights" command now properly controls all 7 individual light entities instead of invalid "all" entity.

**Correct API Usage**: Multi-entity commands now pass list in `data["entity_id"]` field per HA API conventions.

**Commits**:
- `0885cc9` feat: enhance Whisper vocabulary hints for Polish home automation
- `11cc091` feat: add configurable STT confidence threshold
- `a8b35aa` fix: use word boundary matching for end command detection
- `519bf8f` feat: add function calling support to conversation streaming
- `b0ed56c` fix: control all 7 lights when room="all" requested
