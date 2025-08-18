<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

This project is a Vite + React + TypeScript web app for an interactive infrastructure diagram. Goals:
- Data-driven diagram (nodes = systems, services inside, color-coded by category: infrastructure, ingestion, processing, handling, docker)
- Clickable boxes open a right-side details drawer with metadata (description, IP, ports, status placeholders)
- Responsive, keyboard accessible, themable (light/dark) UI
- Modern styling with CSS variables and subtle transitions.

When suggesting code:
- Prefer functional components + hooks.
- Keep components small and focused.
- Use TypeScript types for data models (Node, Service, Link, Category enum).
- Emphasize accessibility: roles, aria-* labels, focus management for drawer.
- Avoid large UI libraries; rely on modern CSS + small utilities.
- Provide example data in src/data/diagram.ts.
