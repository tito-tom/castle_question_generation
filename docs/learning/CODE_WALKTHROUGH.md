# Read the implementation from Python to React to the worker

Use this beside your editor. Line references describe the inspected checkout and will move as code changes. Links open the real source; the tables explain statements or related declaration groups without copying whole files. [Contracts](ROUTES_AND_CONTRACTS.md) gives the corresponding inputs/outputs.

## 1. A small JavaScript and TypeScript bridge

Before React, learn the language around it:

| Code | Python analogy / explanation |
| --- | --- |
| `const x = ...` | Bind a name that cannot be reassigned; the referenced object can still be mutable |
| `let x = ...` | Reassignable local binding |
| `const f = (x: number): number => x + 1` | Similar to `def f(x: float) -> float: return x + 1`; arrow function syntax |
| `{name: 'clip', duration: 25}` | Object with named properties; closest everyday analogy is a dict, accessed with `obj.name` |
| `const {video_id} = result` | Extract a named property into a variable |
| `const [value, setter] = pair` | Sequence unpacking |
| `a.map(f)` | Roughly `[f(x) for x in a]` |
| `a.filter(predicate)` | Roughly `[x for x in a if predicate(x)]` |
| `a.some(predicate)` | Roughly `any(predicate(x) for x in a)` |
| `[...old, item]` | New array containing old elements and one new element |
| `{...old, status: 'ready'}` | New object with old properties, then replaced/added status |
| `x === y` | Strict equality, avoids coercive `==`; object equality still compares identity |
| `a && b`, `a || b`, `!a` | Short-circuit and/or/not; return operand values |
| `x ? a : b` | Python's `a if x else b` |
| `obj?.field` | Optional access, yields undefined if obj is null/undefined |
| `value ?? fallback` | Fallback only for null/undefined; unlike `||`, preserves 0, false, empty string |
| `` `job ${id}` `` | Template string, analogous to `f"job {id}"` |
| `null` / `undefined` | Two absence values; not exactly one-to-one with Python `None` |
| `Promise<T>` | A future eventual result; `await` obtains it or throws its rejection |
| `try/catch/finally` | Python try/except/finally |
| `export` / `import` | Module's public exports / imports; named and default exports differ |

`interface VideoItem { video_id: string }` describes an object shape. It does not construct an object or validate a server response at runtime. A TS `type` or `interface` is erased from executable JavaScript. Pydantic does runtime validation on the Python side.

`number` covers ordinary JavaScript numbers; TS does not distinguish Python `int`/`float` here. `VideoItem[]` means an array of VideoItem. `VideoItem | null` is a union. `field?: string` permits an absent field; `field: string | null` requires the property but permits an explicit null. `Record<string,string>` describes string keys and values. `A & B` combines requirements of both types. `<T>` is a generic type parameter.

`React.FC<Props>` is a type annotation for a function component. JSX such as `<VideoPlayer video={selectedVideo} />` describes a UI element. It is not a Python function invocation syntax and not raw HTML parsed by the browser. The toolchain transforms JSX into JavaScript calls React can interpret.

## 2. React's execution model

A component is a function React calls to calculate UI. It may be called many times. Values in ordinary local variables are recreated on each call. React hooks preserve state or references between calls.

```tsx
const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
```

`useState` returns the current value and an updater. `null` is the initial value. Calling `setAnalysis(newValue)` requests a render; it does not mutate the already running function's `analysis` variable. State is a snapshot for that render.

```tsx
setLocalSelections(prev => [...prev, selection]);
```

The functional update receives the latest previous state. A new array tells React about the change without mutating the old snapshot.

```tsx
const currentJobRef = useRef({ cancelled: false });
```

A ref keeps a stable container with a mutable `.current`. Changing it does not request rendering. Use state for visible UI, refs for imperative handles/current values that callbacks need.

```tsx
useEffect(() => {
  // synchronize with something outside rendering
  return () => { /* cleanup */ };
}, [dependency]);
```

An effect runs after rendering commits, when its dependencies change. Cleanup runs before a changed effect is re-established or when unmounting. `[]` means it has no reactive dependencies, not that development StrictMode can never re-run its setup. Effects are for synchronization, not a replacement for every calculation or event handler.

Props are arguments from parent to child. Callbacks passed as props let children report events upward. `App` owns analysis state; `TimelineView` receives it. A button invokes a callback; the callback updates parent state; React re-renders the affected UI.

Hooks must be called at the component/custom-hook top level in consistent order. Do not put `useState` inside an if or a loop. Ordinary helper functions and event handlers do not use that rule unless they themselves call hooks.

## 3. Your open tab: main.tsx, every executable statement

Source: [main.tsx](../../frontend/src/main.tsx).

| Line | Meaning |
| --- | --- |
| 1 `import React from 'react'` | Import React namespace, used for StrictMode wrapper |
| 2 `import ReactDOM from 'react-dom/client'` | Browser mounting API; different responsibility from React component definitions |
| 3 `import { App } from './App'` | Named export; braces match `export const App` |
| 4 `import './index.css'` | Import stylesheet for its side effect; there is no bound JS variable |
| 6 `ReactDOM.createRoot(...)` | Find the HTML mount point and create a React root |
| 6 `document.getElementById('root')!` | DOM lookup can return null; TS `!` asserts non-null to compiler, but does not add a runtime check |
| 6 `.render(` | Ask root to render this element tree |
| 7 `<React.StrictMode>` | Development checks help expose lifecycle problems; not a visual element |
| 8 `<App />` | Render the main component, no props passed |
| 9 `</React.StrictMode>` | Close wrapper |
| 10 `);` | Close render call |

`frontend/index.html` supplies the element with `id="root"`. In production, Vite emits assets; Nginx serves them. Node/Vite is a development/build tool; the user's browser executes the resulting application JavaScript.

## 4. Your open tab: Header.tsx

Source: [Header.tsx](../../frontend/src/shared/components/Header.tsx).

| Lines | What to understand |
| --- | --- |
| 1 | React import supports the `React.FC` annotation |
| 2 | Import two icon components from a package, not image files loaded with a URL |
| 4 | Export a component with no props; arrow function is the component body |
| 5 | Return JSX |
| 6 | Semantic HTML header with Tailwind classes: bottom border, dark background, sticky top, stacking order, padding, flex layout |
| 7–11 | Flex container and decorated icon box; `<Video ... />` renders an SVG icon |
| 12–19 | Nested containers, title, and Local-first badge; ordinary text nodes become visible content |
| 20–22 | Subtitle text; this copy mentions review/export even though the current App's primary tabs are understanding/questions |
| 23–25 | Close left-side containers |
| 27–33 | Right-side privacy label; `hidden sm:flex` hides at the smallest viewport and shows a flex layout at the configured `sm` breakpoint |
| 29 | Shield icon styled independently from adjacent text |
| 30 | Static claim about original local media; no privacy mechanism is implemented in the Header itself |
| 34–37 | Close JSX, return, and function |

There is no state or network request here. It is a presentational component. CSS classes are declarative styling instructions: `px-6` changes horizontal padding; `flex` establishes a layout model; `items-center` aligns children on the cross axis. Learn layout concepts rather than memorizing every utility name.

## 5. Your open tab: shared/types/index.ts

Source: [types](../../frontend/src/shared/types/index.ts).

| Lines | Definition | Why it matters |
| --- | --- | --- |
| 1–5 | Job/review/session string-union states | Compiler catches misspelled state labels; job cancellation still maps into the four declared job states |
| 7–21 | `VideoItem` | Server media identity and measured metadata; optional fields cover richer/temporary responses |
| 23–31 | `VideoIntervalSelection` | A browser interval belongs to a source reference and stores start/end/duration |
| 33–36 | `ExtractionMethod` | Allowed extraction provenance labels |
| 38–42 | `TemporalAlignmentStatus` | How confidently clip time maps back to original time |
| 44–67 | `StagedClipItem` | Prepared local clip with bytes/preview URL, measured timing, method, original-source identity/bounds, uncertainty and capture metadata |
| 69–79 | `LocalVideoItem` | Browser `File` and object URL; discriminant `sourceType:'local'`; unique source-instance ID |
| 81–83 | `ServerVideoItem extends VideoItem` | Extends server data with `sourceType:'server'` for a discriminated union |
| 85 | `ActiveVideoSource` | Either local or server; narrow before accessing variant-specific properties |
| 87–89 | `isLocalVideo` | Runtime null/type-tag check plus TS type predicate; inside a successful branch TS permits local-only fields |
| 91–98 | `formatFileSize` | Actual runtime helper among declarations; detailed below |
| 100–111 | `InferenceJob` | Browser view of queue status; it intentionally omits internal claim/payload details |
| 113–125 | `GeneratedQuestion` | Question text, nullable answer, event index, evidence, generator/review metadata |
| 127–134 | `QuestionGenerationResponse` | Whole generation record and candidate list |
| 136–152 | `ObservableEvent` | Event text and clip/source timing plus object/action/confidence/provenance |
| 154–177 | `VideoAnalysis` | Summary/events and source/model/runtime/persistence metadata |
| 179–196 | `VideoQAAnswer` | Retained grounded QA response; heuristic confidence and event references |
| 198–216 | `EventReviewItem` | Original event snapshot, review status, optional edits |
| 218–230 | `QuestionReviewItem` | Original question/answer, evidence, review status, optional edits |
| 232–end | `AnnotationReviewSession` | Collection of review items linked to analysis/generation/video and overall status |

Read every field in a declaration as `name: allowed type`. Required identity/interval fields are the backbone; optional metadata lets different lifecycle stages provide what is known. A local File cannot be reconstructed from its filename alone after a refresh. The interface does not persist it.

`formatFileSize`, statement by statement:

1. Accept a numeric byte count and promise a string return.
2. For nonpositive/NaN input return `'0 B'`.
3. Set base 1024 and unit labels.
4. Compute `i = floor(log(bytes)/log(1024))` to select the power/unit.
5. Divide by `1024**i` to obtain a scaled value.
6. Format zero or one decimal place, then append unit.

It is a presentation helper with assumptions (ordinary finite file sizes within the listed units), not a universal numeric validator. Learn to recognize the difference.

Compare shared types with backend schemas when changing API fields. These TS declarations are manually maintained; there is no automatic guarantee that the API and frontend cannot drift. The HTTP client uses declared generic types, not a runtime TS schema parser.

## 6. Your open tab: shared/api/client.ts

Source: [client.ts](../../frontend/src/shared/api/client.ts). This module is the browser's adapter to HTTP. It is an exported object with methods, not a Python class and not a database connection.

### Imports, credentials, and response helper (lines 1–40)

| Statement | Meaning |
| --- | --- |
| Type imports | Describe what responses are expected to look like |
| `const API_BASE = '/api/v1'` | Relative URL; same browser origin, with Vite/Nginx proxy routing requests to Python |
| `let activeSessionId ... = null` | Mutable module memory shared by this loaded client module |
| `let activeSessionToken ... = null` | Temporary authorization token; not React state and not persisted localStorage |
| `getAuthHeaders(): Record<string,string>` | Build HTTP header object each time from current module credentials |
| `if (activeSessionId)` | Add ID header only when a truthy value exists |
| `if (activeSessionToken)` | Add token header only when available |
| `return headers` | Caller can spread these headers into a request |
| `handleResponse<T>(res): Promise<T>` | Generic helper to return typed JSON or throw an error |
| `if (!res.ok)` | fetch does not reject merely for HTTP 400/500; check status explicitly |
| Default error string | Includes HTTP status and status text |
| `await res.json()` inside try | Try parsing FastAPI's error JSON |
| `typeof body.detail === 'string'` | Preserve readable server text; stringify structured validation details otherwise |
| Empty `catch` | Keep fallback message when body was not JSON |
| `throw new Error(errorDetail)` | Reject the async function; upstream `catch` can show an error |
| `return res.json()` | Decode successful JSON; `<T>` does not verify the decoded value at runtime |

### API object reading map

| Lines / method | Explanation |
| --- | --- |
| 42–56 credential methods | Set/get/clear module values. `undefined` means leave a field unchanged; passing `null` explicitly clears it |
| 59 `getVideos` | GET list with auth headers, await response, return decoded result |
| 66 `uploadVideo` | FormData with file, POST permanent upload route; no explicit auth headers in this method |
| 76–160 `uploadTemporaryClip` | Detailed event-based XHR upload below |
| 162 `deleteTemporaryClip` | DELETE clip; returning deletion status can reflect deferral |
| 170 `touchSession` | POST activity with effective token; copies auth header object before changing it |
| 182-ish `getVideoStreamUrl` | Builds URL for media element; includes token query for temporary IDs because a video src cannot simply use client fetch headers |
| 197 `submitVideoUnderstanding` | JSON POST with video ID/fps, content type and credentials; returns job acknowledgement |
| 209 `submitQuestionGeneration` | JSON POST with analysis/duration/count/criteria; starts worker path |
| 231 `getQuestionGeneration` | GET persisted generation by ID |
| 238 `getJobStatus` | GET queue status |
| 245 `cancelJob` | DELETE job route; does not mean delete SQL row |
| 253–266 `pollJobUntilFinished` | Loop until terminal job; await a timer between reads |
| 269 `getAnalyses` | GET analysis summaries |
| 276 `getAnalysis` | GET full analysis |
| 283 `mergeWindowAnalyses` | POST window IDs/source timing; returns merged record summary |
| 297 `saveAnalysisPersistent` | POST retention action and return updated analysis |
| 309 `askVideoQuestion` | JSON POST question plus optional analysis ID |
| 321 `askAnalysisQuestion` | JSON POST question against a specific analysis |
| 334 `createOrLoadReviewSession` | POST linked IDs to initialize/retrieve review |
| 354 `getReviewSession` | GET complete review |
| 361 `updateEventReview` | PATCH editable event fields/status at an index |
| 377 `updateQuestionReview` | PATCH editable question fields/status |
| 393 `updateSessionStatus` | PATCH overall status/summary |
| 409 `syncReviewSessionQuestions` | POST generation ID to merge questions into review |
| 424 `saveQuestionGenerationPersistent` | POST save action; return type `any` gives up useful type checking here |
| 437 `saveReviewSessionPersistent` | POST save action for review |
| Final two export URL methods | Construct JSON/CSV download URLs, adding an encoded token; they do not themselves fetch a file |

For each JSON method, the pattern is the same: template URL → HTTP method → headers → `JSON.stringify(body)` → `fetch` → `handleResponse`. `JSON.stringify` serializes an object to bytes/text suitable for HTTP; `res.json()` does the inverse parsing.

### Temporary upload line groups (76–160)

1. Signature takes a `File`, optional metadata object, optional progress callback, and returns a Promise of server metadata/session fields.
2. `new Promise((resolve,reject) => ...)` adapts callback-driven XHR into an awaitable result.
3. FormData appends binary file and effective credentials. Explicit metadata wins over module credentials using `||`.
4. Optional fields are appended only when available. Numeric/boolean values become strings because these are form fields.
5. `new XMLHttpRequest()` and `.open('POST', url)` configure the request.
6. `.setRequestHeader` attaches credentials as headers in addition to form values.
7. `xhr.upload.onprogress` calculates percent only when total length is computable; callbacks update UI without resolving the upload Promise.
8. `xhr.onload` checks a 2xx status range. A network-complete event can still contain an HTTP error.
9. Success JSON is parsed. Token response header fills a missing response field. Module credentials are updated before resolving.
10. Parse failure rejects with a readable error; HTTP failure tries to extract server detail before rejecting.
11. `xhr.onerror` rejects network-level failure.
12. `xhr.send(formData)` starts the upload. Before this line, all event handlers are just registered functions.

### Polling, line by line in execution order

```tsx
while (true) {
  const job = await this.getJobStatus(jobId);
  if (onUpdate) onUpdate(job);
  if (job.status === 'completed' || job.status === 'failed') {
    return job;
  }
  await new Promise(r => setTimeout(r, intervalMs));
}
```

`while(true)` repeats without a fixed count. The first await gets current status. An optional callback observes every response. A terminal condition returns, ending both loop and async method. Otherwise `setTimeout` schedules Promise resolution after the interval; awaiting it yields control rather than freezing the browser. `this` relies on calling it as `api.pollJobUntilFinished(...)`; detaching a method can change `this` binding.

This helper has no abort/timeout. A UI stale-result flag around it suppresses application of its eventual result but does not stop these HTTP polls. This is a useful example of separate layers of cancellation.

## 7. Your open tab: App.tsx

Source: [App.tsx](../../frontend/src/App.tsx). Read it as a state coordinator, event-handler collection, and render tree. It is not a URL-routing table.

### Imports and state (lines 1–68)

| Lines | Explanation |
| --- | --- |
| 1–28 | Import React/hooks, icons, API, shared shapes, and feature components. Named imports match exports in other files |
| 29 | Define/export main function component |
| 30 | Video library list, initially empty |
| 31 | Selected server video or null |
| 32 | Which source is active: local/server/none |
| 33 | Loaded analysis or null |
| 35 | Current player time, initially zero |
| 36 | Requested seek time or null |
| 37 | Richer seek request adds playback intent and unique request ID |
| 38 | Highlighted/previewed interval, inline object shape |
| 41 | User's interval selection list |
| 42 | Measured local duration |
| 45 | Prepared clip with browser file reference |
| 46 | Metadata from backend upload; intersection combines base type with session fields |
| 47–52 | Modal visibility and interval being prepared |
| 54 | Server-video analysis busy flag |
| 55 | Question generation busy flag |
| 56 | Active results tab |
| 59 | Staged local clip analysis busy flag |
| 60 | Numeric upload percent or null when not uploading |
| 61 | Human-readable processing step |
| 62 | Displayable failure or null |
| 63 | Mutable stale-result cancellation marker |
| 66–68 | Refs mirroring current source state for asynchronous callbacks |

State variables are not independent stored database fields. They are the current browser view. Reloading loses these in-memory values unless something explicitly reloads/persists them.

### Local-video hook and startup (70–139)

| Lines | Explanation |
| --- | --- |
| 70–78 | Destructure the hook's object return into values/functions/input ref |
| 78–85 | When a new local file is selected, mark previous clip operation stale, replace marker object, reset busy/progress/error |
| 87–98 | Set source refs/state to local; discard previous upload/analysis/seek/selections/duration so old evidence is not shown for a new file |
| 100–104 | Functional staged-clip update revokes prior URL and clears clip |
| 107–117 | Effects mirror current React values into refs |
| 120–122 | Initial effect starts library fetch |
| 124–139 | `loadVideos` awaits list, stores it, optionally selects first server video only if no newer local/server choice was made; logs failure |

A closure captures variables from a particular render. While a network request waits, the user can select another source. Reading current refs in the result handler reduces the chance an old initial load overwrites a newer user selection. This is asynchronous state correctness, not model behavior.

### Source/extraction handlers (141–245)

| Function | Execution order |
| --- | --- |
| `handleSelectServerVideo` (141) | Mark old clip workflow stale → clear progress/staging and revoke URL → select server source → clear previous evidence/player state → try loading existing analysis using video ID; missing analysis is tolerated |
| `handleSelectLocalVideo` (170) | If local file already exists, switch source and reset player/evidence; otherwise open picker |
| `handleClearLocal` (183) | Invalidate workflow → revoke staged URL → clear hook/file → reset selections/player → select first server video if available, otherwise no source |
| `handleOpenExtraction` (211) | Reject interval longer than source limit → record interval → show modal |
| `handleClipStaged` (217) | Invalidate previous operation → clear previous analysis/upload → revoke replaced staged URL → store new clip |
| `handleClearStagedClip` (233) | Invalidate operation → reset progress/error → revoke URL → clear staging |

`URL.revokeObjectURL` releases the browser URL mapping; it does not delete the user's original file. File/URL ownership and cleanup are part of correctness even in frontend code.

### Analyze the staged clip (248–341), detailed execution

| Statement group | Meaning and reason |
| --- | --- |
| Early guard | Only a local source with a staged clip and no active clip analysis can proceed |
| Duration guard | Store error and return if above 600-second source limit |
| Size guard | Store error and return if above 1 GiB |
| Mark old reference cancelled | Old asynchronous callbacks must not publish stale results |
| `const currentJob = {cancelled:false}` | Create a distinct marker object captured by this invocation |
| Store marker in ref | Future selection changes can invalidate this specific operation |
| Set busy/progress/text/error | Render upload state immediately |
| Initialize `uploadedVideoId`, `jobWasSubmitted` | Track how much backend work exists for error cleanup |
| `await api.uploadTemporaryClip(...)` | Send only prepared clip and provenance; progress callback checks marker before setting UI state |
| Save returned ID | Needed if upload succeeded but job submission later fails |
| If cancelled after upload | Request temporary media deletion, tolerate cleanup failure, stop applying this operation |
| Switch progress text | Upload finished; now submitting work |
| `await api.submitVideoUnderstanding(...)` | Create queued job and remember submission happened |
| Cancelled guard | Prevent later UI changes after source switch; does not call `api.cancelJob` |
| Update analysis text | Render worker processing state |
| `await api.pollJobUntilFinished(job_id)` | Wait for terminal queue state through repeated HTTP reads |
| Cancelled guard | Do not attach old evidence to a new source |
| Completed branch | Require result ID, retain uploaded metadata, GET analysis |
| Guard after GET | Source can change even while fetching the completed result |
| `setAnalysis`, `setActiveTab` | Publish analysis and show understanding tab |
| Failed branch | Turn terminal backend error into thrown JS Error |
| `catch` cleanup | If upload exists but no job was submitted, request deletion; avoid deleting media an active job may need |
| `catch` UI handling | Log/set error only if this invocation is still relevant |
| `finally` | Reset busy/upload state only for relevant invocation |

This function mainly returns `Promise<void>`; its useful outputs are UI state changes and backend side effects. It is a workflow coordinator. If you extracted it into a custom hook later, preserve those cancellation/cleanup semantics.

### Selection and server/question handlers (344–434)

| Lines | Explanation |
| --- | --- |
| 344–347 | Jump: set seek request including autoplay flag/ID and legacy seek time |
| 349–353 | Preview: activate interval and request autoplay from its start |
| 355–358 | Add selection using new array and activate it |
| 360–365 | Update matching selection using `.map`, preserve other items |
| 367–380 | Remove matching ID using `.filter`; clear active interval if it corresponds within tolerance |
| 382–400 | For selected server video: set busy, submit job, poll, load completed analysis, log exceptions, clear busy |
| 402–406 | Choose clip duration based on server metadata, upload/staged metadata, source interval, or fallback |
| 408–409 | Require existing analysis and set question busy flag |
| 412–417 | Submit async generation with analysis ID, duration, maximum five, criteria |
| 418–423 | Poll; load generation if completed with ID; otherwise throw |
| 424–428 | Normalize thrown value into Error; always clear busy |
| 431–434 | Timeline selection updates active interval and seeks to interval start |

The server analysis branch is simpler than the staged branch and does not have identical stale-result/error handling. Do not assume every similar handler has the same guarantees. These observations are reading notes, not code changes made by this guide.

### Render tree (436–end)

Read JSX in nested chunks:

1. Outer page wrapper supplies background, text, and flex layout.
2. Hidden file `<input>` uses `fileInputRef`; `onChange` picks the first selected file via optional chaining, then delegates to hook `selectFile`.
3. `<Header />` renders static shared header.
4. Main responsive grid contains video controls/player on left and results on right.
5. Library area maps `videos` to buttons. `key={v.video_id}` gives React stable sibling identity; it is not a prop read by the button.
6. Conditional `localVideo && (...)` renders local source controls. A ternary renders empty-library messaging or list buttons.
7. `<VideoPlayer>` receives local OR server props according to active source, plus seek/interval state and callbacks. Passing `setCurrentTime` as a callback lets the child report playback time upward.
8. `<ClipSelectionPanel>` only renders for a local source; it receives selections and operations as props.
9. `<StagedClipCard>` only renders when a prepared clip exists; analyze/retry callbacks call the same staged workflow.
10. Source-specific banners/actions render local metadata or server analysis controls. `disabled={isAnalyzing}` prevents repeated button interaction while busy.
11. Tab buttons set `activeTab`. Conditional class strings choose active/inactive styling.
12. Both result panels remain in JSX; CSS `hidden` toggles visibility. Hiding is different from unmounting: a mounted child's internal state can survive tab switches.
13. `<TimelineView>` receives analysis and interval callback; its analysis action depends on current source/staged clip.
14. `<QuestionGenerationWorkspace>` receives analysis, busy state, and `onGenerate` callback. The child invokes it with criteria text and handles returned generation/error.
15. Modal renders conditionally when local video exists and extraction is open; props provide target/default interval, close action, and staged-clip callback.

For any individual JSX line, distinguish four roles: an element/component name, props (including callbacks), styling (`className`), and children. Braces enter JavaScript expressions; parentheses group them; `/>` closes an element with no children. JSX comments use `{/* ... */}`.

## 8. Hook implementation: useLocalVideo.ts

Source: [useLocalVideo.ts](../../frontend/src/features/videos/useLocalVideo.ts).

The result interface declares what the hook returns. `isSupportedVideoFile` accepts a video MIME prefix or common extension; this is a user-friendly preliminary check, not proof of valid/decodable media. Source IDs prefer `crypto.randomUUID` with a fallback, distinguishing different opened instances even if filenames match.

Inside the hook:

1. Two `useState` calls store video/error; two refs own URL and file input.
2. `cleanupObjectUrl` uses `useCallback` to keep a stable function and revoke/reset a live mapping.
3. Effect returns cleanup, so unmount releases the current mapping.
4. `clearLocalVideo` cleans URL, clears state, resets input so the same file can be selected again.
5. `selectFile` rejects missing/empty/unsupported file; cleans previous mapping; creates a new URL in try/catch; builds `LocalVideoItem`; stores it; calls optional parent callback; returns true.
6. `openFileDialog` resets input value then clicks its DOM node through a ref.
7. Return object exposes state/functions/ref to App. Custom hooks compose React hooks; they are not server services.

## 9. FastAPI and Pydantic using a real route

Source: [jobs.py](../../backend/src/castle_qa/api/routers/jobs.py), [job_schema.py](../../backend/src/castle_qa/api/schemas/job_schema.py).

```python
@router.post(
    "/question-generations",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
```

The decorator registers a Python function for an HTTP method/path. Router prefix `/jobs` and app prefix `/api/v1` combine with it. `response_model` shapes/validates output; status 202 describes queued work. The neighbouring singular decorator registers an alias for the same handler.

```python
request: QuestionGenerationJobRequest
repository: Annotated[JobRepository, Depends(get_job_repository)]
```

The request argument is parsed from JSON into Pydantic. The repository argument is supplied by calling the dependency provider. The browser does not send a repository object. `Annotated` adds framework metadata to a Python type.

Handler body, in order:

1. Load requested analysis through the workflow.
2. If absent, raise `HTTPException(404, ...)`; FastAPI serializes an error response.
3. Call the domain job factory with request values.
4. `repository.create(job)` commits queued work.
5. Return a response model containing ID and queued status.

A schema such as `clip_duration_seconds: float = Field(gt=0, allow_inf_nan=False)` enforces finite positive input before this body runs. These runtime checks are stronger than a Python annotation alone. Domain factories can also validate their own invariants because they may be called outside HTTP.

In [api/main.py](../../backend/src/castle_qa/api/main.py), `create_app` loads settings, constructs FastAPI, adds body-size middleware, and includes routers. `app = create_app()` exposes the ASGI application Uvicorn imports. Lifespan code starts/stops optional maintenance. Heavy inference is not executed by route registration.

## 10. Extractor: every algorithmic step

Source: [video_clip_extractor.py](../../backend/src/castle_qa/services/video_clip_extractor.py).

| Statement | Explanation |
| --- | --- |
| Constructor stores probe and output directory | Collaborators/state on an OOP instance, already familiar from Python |
| `output_dir.mkdir(parents=True,exist_ok=True)` | Ensure output location exists; constructor has a filesystem side effect |
| `get_duration(request.video_path)` | Ask ffprobe wrapper about real media |
| `center = request.timestamp.seconds` | Convert timestamp abstraction to numeric seconds |
| Reject center beyond duration | Avoid selecting a center outside media |
| `start = max(...)` | Clamp lower edge at beginning |
| `end = min(...)` | Clamp upper edge at file end |
| `duration = end - start` | Actual requested output duration after clamping |
| `_build_output_path` | Source stem plus sanitized timestamp, `.mp4` extension |
| `_run_ffmpeg(...)` | Perform external processing; raises on nonzero process exit |
| `return ClipResult(...)` | Return data object linking media output to source timing |
| `command = [...]` | Argument list avoids assembling a shell-interpreted command string |
| `-y` | Overwrite matching output without prompting on this server path |
| `-ss` | Start position |
| `-i` | Input media |
| `-t` | Output duration |
| `-c:v libx264`, `-c:a aac` | Re-encode video/audio using selected codecs |
| `subprocess.run(command,check=True)` | Wait for process, raise `CalledProcessError` on failure |

An operation can return metadata and still have its main product be a file. Tests should check boundaries/command behavior, not merely that `ClipResult` can be constructed.

## 11. Worker execution: what to inspect

Source: [entrypoint.py](../../backend/src/castle_qa/workers/entrypoint.py), [job_worker.py](../../backend/src/castle_qa/workers/job_worker.py), [worker_runner.py](../../backend/src/castle_qa/workers/worker_runner.py).

`main()` parses CLI flags, configures logging, and chooses demo/live worker. Demo creates temporary storage/schema and a fake handler; live uses configured repositories. `create_job_handler` chooses mock or real service implementations and constructs workflows. This is the composition root: the place concrete objects get wired together.

For one `process_next()` call:

1. `claim_next(worker_id=...)`: get owned running job or return `None`.
2. Construct a threading `Event` and heartbeat function closure.
3. Heartbeat loop waits interval, then updates only while claim token remains valid.
4. Construct daemon thread, then start it inside try before handler call.
5. Reject unsupported job types.
6. Execute injected handler. It must return nonempty result ID; question IDs must match `gen_` format.
7. On exception, log full traceback, mark job failed with safe generic message, run terminal callback, return refreshed domain job.
8. In finally, signal heartbeat stop and join briefly.
9. Check cancellation request; finalize as failed when requested.
10. Otherwise mark completed with claim token, ensuring only current owner can write terminal success.
11. Fetch updated job, run terminal callback, return.

The heartbeat thread uses the database independently of slow model execution. Ownership checks protect terminal transitions; they do not alone make every downstream file write exactly-once. An external side effect may already have happened before failure or cancellation is recorded.

## 12. Model adapter: read the tensor code without being an ML expert

Source: [local Qwen adapter](../../backend/src/castle_qa/services/video_understanding/local_qwen_video_understanding_service.py).

| Expression | Meaning |
| --- | --- |
| Import inside `__init__` | Delay requiring torch/Transformers until a real service is created |
| CUDA check | Fail clearly if real inference cannot execute in expected environment |
| Prompt `.read_text` | Instructions are data loaded from a text file |
| `AutoProcessor.from_pretrained(model_name,...)` | Load model-specific tokenizer/media preprocessing configuration |
| Model `.from_pretrained(...)` | Load pretrained parameters; first run may download/cache files |
| `dtype=torch.bfloat16` | Use reduced precision for parameter/computation memory characteristics |
| `device_map="auto"` | Delegate placement strategy to supported library tooling |
| `sampling_fps = min(...)` | Bound requested video-frame budget across full clip |
| `messages = [...]` | Structured chat input with a video and instruction text |
| `apply_chat_template(...,return_tensors="pt")` | Format/preprocess into PyTorch tensors |
| `inputs.to(self._model.device)` | Place input tensors for model execution |
| `torch.inference_mode()` | Disable gradient tracking needed during training; ordinary inference does not train |
| `_model.generate(**inputs,...)` | Autoregressively produce output token IDs |
| `output[len(input_ids):]` | Remove echoed prompt token prefix |
| `batch_decode(...)` | Token IDs → human-readable strings |
| `_parse_json(response)` | Text → dictionary; handles some code fences/wrappers, raises on invalid JSON |
| Add provenance fields | Record mock/real mode, runtime, device, effective sampling |
| `VideoAnalysis.from_dict(...)` | Dictionary → domain object and nested Event objects |

The variable printed as “Peak GPU memory” currently uses `memory_allocated()` after inference, not `max_memory_allocated()`. Logging labels can be misleading; inspect the actual function when interpreting metrics.

## 13. A real test, line by line

Source: [test_api_health.py](../../backend/tests/test_api_health.py).

```python
from fastapi.testclient import TestClient
from castle_qa.api.main import create_app

def test_health_check():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "castle-qa-studio-api",
    }
```

1. Import a client that can call the ASGI application in the test process.
2. Import app factory so the test owns its app instance.
3. `test_` naming makes pytest discover the function.
4. Create application: arrange.
5. Context manages app/client lifecycle.
6. Simulate HTTP request: act; no externally listening Uvicorn is needed.
7. Check success status: one part of the contract.
8. Check exact JSON shape/values: another part of the contract.

If the endpoint accidentally returns a different service name, the second assertion catches it even though the status stays 200. This test does not inspect Qwen readiness.

Next read `test_job_worker.py`: fixtures create a temporary SQL schema/repository; injected fake handler reads the job and asserts it was committed as running **before** inference starts. That tests a meaningful sequencing guarantee across real database operations.

In `question_generation_workspace.test.tsx`, identify arrange/render → user action → mocked async response → `waitFor` assertion. In browser specs, identify the same shape but with an actual `page` and live stack. The test runner, DOM simulator, assertion library, and application mock are separate collaborators.

`frontend/tsconfig.json` includes `src`, not the whole tests directory. A passing frontend production build therefore does not necessarily mean every test file's props are type-correct; Vitest's transformation is also not equivalent to a full `tsc` check of all tests.

## 14. Continue through the rest of the code

Use [SOURCE_ATLAS.md](SOURCE_ATLAS.md) to find every Python function/method signature, then use this order for a new file:

1. Read its imports to identify responsibilities/collaborators.
2. Read its input/output type or dataclass.
3. Read public methods before private helpers.
4. Mark validation, branching, side effects, and error conversion.
5. Find call sites with `rg -n 'function_name' backend frontend`.
6. Read its tests and predict observable outcomes.

Do not learn repeated JSX padding classes before understanding which state changes make the component visible. Do learn resource cleanup, runtime boundaries, timestamp units, ownership, and error propagation: those details decide whether generated code behaves correctly.
