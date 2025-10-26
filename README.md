
# CyVitals Workspace

This repository now hosts both the original CyVitals Python tooling and the new Figma-derived React dashboard.

```
.
├── backend/      # Python entry point, sensors, imgui shell
└── frontend/     # React dashboard generated from the Figma export
```

## Frontend (React Dashboard)

```bash
cd frontend
npm install
npm run dev     # start the Vite dev server on http://localhost:3000
npm run build   # create production assets in frontend/dist
```

The generated UI lives entirely under `frontend/src`, with shared helpers in `frontend/src/components`.

## Backend (Python Toolkit)

```bash
python -m backend.main
```

The backend installer will bootstrap required Python packages before launching the existing ImGui interface.

## Design Credits

The dashboard UI was exported from the original Figma project: https://www.figma.com/design/Gelh7hLA9UMq0PxApqrW5r/Biomedical-Lab-Dashboard.
  
