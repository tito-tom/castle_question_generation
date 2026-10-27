# CASTLE QA Studio Testing Guide

This guide describes the automated checks available in the repository and the areas they cover. Test totals are intentionally omitted because they change as the suite evolves.

## Automated checks

Run commands from the repository root after installing the backend and frontend dependencies.

### Backend

~~~bash
python -m pytest backend/tests
~~~

Backend tests cover API routes, upload limits, video probing, temporary storage lifecycle, job queue behavior, analysis provenance, question generation, and evidence grounding. Tests use mock inference and isolated storage; they do not download Qwen weights or require a GPU.

### Frontend unit and component tests

~~~bash
npm --prefix frontend test
~~~

These checks cover local-video handling, interval selection and extraction, criteria import, question editing and copying, and result rendering.

### Production build

~~~bash
npm --prefix frontend run build
~~~

This runs TypeScript type checking and creates the production Vite bundle.

### Browser end-to-end tests

Start the local API, mock worker, and frontend, then run:

~~~bash
npm --prefix frontend run test:e2e
~~~

The end-to-end suite requires the browser configured in frontend/playwright.config.ts and the application services on their configured local ports.

## GPU inference checks

Automated tests do not validate real CUDA inference. On the GPU host, verify the worker can see the GPU, finish loading the configured model, claim a job, and complete a short clip analysis. The model cache is stored in the named Docker volume configured in compose.gpu.yaml.

## Troubleshooting

- **Connection refused:** confirm API, worker, and frontend services are running.
- **Job remains queued:** inspect worker logs and check that its database volume is the same as the API's.
- **Question-generation failure:** inspect worker logs for the exception; the UI error is intentionally shorter than the traceback.
- **GPU tests unavailable locally:** use mock mode for local development and perform real-inference validation on the configured NVIDIA host.
