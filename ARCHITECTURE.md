# UI State Capture System - Architecture & Design

## Overview

A generalizable AI multi-agent system that automatically navigates web applications and captures UI states for any user-requested task, across any web app.

**Key Innovation:** Parallel LLM planning + parallel login handling = faster, more robust task execution

---

## Current Architecture (v1)

```
User Task Input
    ↓
Browser Use Agent
    ├─ Navigate to URL
    ├─ Login (wait for user code entry)
    └─ Execute task
    ↓
Screenshot Capture (from history)
    ↓
Manifest + Dataset
```

**Limitations:**
- Agent waits for login → then plans steps → then executes
- Sequential planning wastes time during login
- No external context/documentation lookup
- Limited adaptability to app-specific workflows

---

## Proposed Architecture (v2) - Parallel Planning + Execution

### Key Insight
While the agent is **blocking on login**, we can **run a parallel LLM process** to:
1. Search for documentation/tutorials
2. Generate modular step-by-step instructions
3. Have them ready BEFORE login completes

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User Input: "Create a database in Notion"                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
            ┌───────────────┴───────────────┐
            ↓                               ↓
    ┌──────────────────┐          ┌──────────────────────┐
    │ Browser Use      │          │ Parallel LLM         │
    │ Agent (Path A)   │          │ Planner (Path B)     │
    │                  │          │                      │
    │ 1. Navigate to   │          │ 1. Web Search:       │
    │    Notion.so     │          │    "How to create    │
    │ 2. Click Login   │          │     database Notion" │
    │ 3. WAIT 15s ─────┼──────────│─→ 2. Extract docs   │
    │    (user enters  │          │    from Notion blog  │
    │     code)        │          │ 3. LLM generates    │
    │ 4. Continue ─────┼──────────│─→ modular steps     │
    │    Login         │          │ 4. Format steps     │
    │                  │          │    for execution    │
    │ 5. Page loads    │◄─────────├─→ READY (by now!)   │
    │ 6. Execute steps │          │                      │
    │    (from Planner)│          │ Steps:               │
    │                  │          │ - Click "New"        │
    └──────────────────┘          │ - Select "Database"  │
                                  │ - Name it            │
                                  │ - Confirm            │
                                  └──────────────────────┘
                            ↓
                    Screenshot Capture
                            ↓
                    Manifest + Dataset
```

---

## Proposed Implementation: v2 Architecture

### Component 1: Browser Use Agent (LoginAwareAgent)

```python
class LoginAwareAgent:
    async def run_with_planning(self, task: str, planner_queue):
        """
        Execute task while receiving plan from parallel planner
        """
        # Start login flow
        await self.browser.navigate(start_url)
        await self.browser.click_login()
        
        # BLOCKING: Wait 15s for user code entry
        await self.wait_for_login(15)
        
        # By now, planner has generated steps (if ready)
        plan = planner_queue.get_if_available()  # Non-blocking
        
        if plan:
            # Execute pre-generated plan
            await self.execute_steps(plan)
        else:
            # Fallback: generate plan on-the-fly
            # (planner may still be processing)
            await self.generate_and_execute()
        
        # Capture screenshots
        return self.capture_screenshots()
```

### Component 2: Parallel LLM Planner (PlannerWorker)

```python
class PlannerWorker:
    async def generate_plan(self, task: str, app: str, output_queue):
        """
        Generate step-by-step instructions in parallel
        """
        # Step 1: Web search for context
        docs = await web_search(f"{task} {app} tutorial")
        
        # Step 2: LLM generates modular steps
        steps = await llm.generate_steps(
            task=task,
            app=app,
            context=docs,
            format="modular_json"  # JSON format for easy parsing
        )
        
        # Step 3: Put in queue for agent to consume
        output_queue.put(steps)
        
        return steps
```

### Component 3: Web Search Tool Integration

```python
class WebSearchTool:
    async def search(self, query: str) -> List[Result]:
        """
        Search web for documentation + tutorials
        """
        results = await firecrawl_search(query)  # or similar
        return results
    
    async def extract_documentation(self, url: str) -> str:
        """
        Extract structured steps from documentation pages
        """
        content = await firecrawl_scrape(url)
        steps = await llm.extract_steps(content)
        return steps
```

---

## Execution Flow (Detailed)

```
T=0s   | User submits: "Create a database in Notion"
       |
T=0s   | ┌─ Browser Agent starts
       | │  - Navigate to notion.so
       | │
T=2s   | │  - Click Login button
       | │  - Wait for user to enter code (BLOCKING)
       | │
       | └─ Parallel Planner starts
       |    - Search: "How to create database Notion"
       |    - Parse Notion documentation
       |    - LLM generates: [click "New", select "Database", enter name, confirm]
       |    - Put in queue
       |
T=10s  | Planner finishes, steps are ready
       |
T=15s  | Agent: Code entered by user, login complete
       |    - Check queue: Steps are ready!
       |    - Execute steps immediately
       |    - Capture screenshots
       |
T=25s  | Done
```

---

## Why This Approach is Better

### 1. **Parallelism**
- ✅ Uses "idle" time (login wait) productively
- ✅ No wasted time
- ✅ Plan ready when agent needs it

### 2. **Robustness**
- ✅ Fallback: If planner fails, agent still works (generates plan on-the-fly)
- ✅ If planner succeeds, agent gets optimized pre-generated steps
- ✅ Graceful degradation

### 3. **Generalization**
- ✅ Same architecture works for ANY app (Notion, Linear, Asana, etc.)
- ✅ Same architecture works for ANY task
- ✅ LLM + search provides context for any workflow

### 4. **Quality**
- ✅ Steps grounded in real documentation (not just hallucination)
- ✅ Modular steps = fewer errors
- ✅ LLM optimizes action sequences

### 5. **Extensibility**
- ✅ Easy to add new tools (search, extraction, etc.)
- ✅ Easy to swap LLM providers
- ✅ Easy to cache plans for repeated tasks

---

## Alternative Approaches (Considered)

### Option A: Pure Browser Use (Current)
**Pros:** Simple, no external calls
**Cons:** No external knowledge, slower, less context-aware

### Option B: Full Planning Before Login
**Pros:** Simpler flow
**Cons:** Wastes time before login, extra wait for user

### Option C: Parallel Planning + Login (Proposed) ⭐
**Pros:** 
- Uses time efficiently
- Better quality steps (documentation-grounded)
- Generalizable
- Faster overall
**Cons:** Slightly more complex architecture

---

## Implementation Roadmap (v2)

### Phase 1: Foundation
- [ ] Create `PlannerWorker` class with web search integration
- [ ] Create `OutputQueue` for inter-process communication
- [ ] Integrate web search tool (firecrawl or similar)
- [ ] Create LLM prompt for step generation

### Phase 2: Integration
- [ ] Modify `AdvancedUIStateCapture` to use parallel planner
- [ ] Add fallback logic (if planner times out)
- [ ] Test with 3-5 tasks across 2 apps

### Phase 3: Optimization
- [ ] Add step caching (same task = same steps)
- [ ] Add step validation (verify steps make sense)
- [ ] Measure performance improvements

### Phase 4: Testing
- [ ] Capture datasets for 5+ tasks
- [ ] Test across Linear, Notion, Asana
- [ ] Record Loom walkthrough

---

## Generalization for Every App

### Core Principle: Task-Agnostic
The system doesn't need to know app-specific details:

```
Input: "Create a database in Notion"
    ↓
Web Search: "create database notion tutorial"
    ↓
LLM Extract: Common patterns (click, enter text, select, confirm)
    ↓
Browser Execute: Generic click, type, select actions
    ↓
Output: Screenshots of each state
```

### How It Generalizes
1. **Web Search** finds documentation for ANY app
2. **LLM** understands ANY workflow
3. **Browser Agent** executes ANY sequence of interactions
4. **Screenshot capture** works on ANY page

**Result:** Same code, different app = different workflow captured automatically ✅

---

## Example: Multi-App Testing

```bash
# Notion: Create database
python run_capture.py "Create Database" "Create a new database in Notion"

# Linear: Create project
python run_capture.py "Create Project" "Create a new project in Linear"

# Asana: Add task
python run_capture.py "Add Task" "Add a new task to an Asana project"

# GitHub: Create issue
python run_capture.py "Create Issue" "Create a new GitHub issue"
```

All use the same code! 🎉

---

## Questions for Refinement

1. **Step Validation:** Should planner validate steps against app structure?
2. **Caching:** Should we cache plans for repeated tasks?
3. **Error Recovery:** How should agent handle plan steps that fail?
4. **Context Size:** How much documentation context is optimal for LLM?
5. **Timeout Handling:** What's the right timeout for planner before agent gives up?

---

## Next Steps

1. ✅ Current system: Single task, captures screenshots (DONE)
2. ⏭️ **Add parallel LLM planner** (Phase 1)
3. ⏭️ **Integrate web search tool** (Phase 1)
4. ⏭️ **Test on 5+ tasks** (Phase 2)
5. ⏭️ **Record Loom demo** (Phase 3)
6. ⏭️ **Submit** (Phase 4)

---

## Summary

**Current:** Sequential (Navigate → Login → Plan → Execute → Capture)

**Proposed:** Parallel (Navigate+Login in parallel with Plan → Execute → Capture)

**Result:** Faster, smarter, more generalizable system that truly adapts to ANY task on ANY app!

