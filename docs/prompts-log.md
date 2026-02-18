# Claude Code Prompts Log

This document tracks key Claude Code prompts and learnings during the development of the Medical Invoice Parser project.

## Purpose

- Record effective prompts that produced useful implementations
- Note challenges encountered and how they were resolved
- Document architectural decisions and their rationale
- Provide context for future development sessions

---

## Session 1 - Project Scaffolding

### Initial Setup Prompt
**Prompt:** "Read instructions/docs/requirements.md. Help me with Phase 1, Step 1: scaffold the project structure."

**Outcome:**
- Created comprehensive project structure following requirements.md specifications
- Set up React + Vite frontend skeleton
- Set up FastAPI backend skeleton
- Created documentation and configuration files
- Used Conda for Python environment management instead of venv

**Learnings:**
- Using Vite for React provides a fast development experience
- Separating concerns with components and services makes the codebase maintainable
- Pydantic models in FastAPI provide automatic validation and documentation
- Conda provides better environment management for data science projects with complex dependencies

---

## Future Sessions

*(This section will be updated as development progresses)*

---

## Tips for Future Development

1. **Before starting:** Always reference the requirements document to stay aligned with project goals
2. **After implementation:** Test each component independently before integrating
3. **When stuck:** Break down the problem into smaller, testable pieces
4. **API integration:** Test API calls with tools like Postman or curl first
5. **Error handling:** Add meaningful error messages for better debugging

---

## Notes

- Last updated: 2025-02-18
- Current phase: Phase 1 - End-to-End with MinerU Online API
- Environment: Conda for Python, npm for Node.js
