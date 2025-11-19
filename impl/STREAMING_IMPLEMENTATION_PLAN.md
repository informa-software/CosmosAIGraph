# Streaming Implementation Plan for Query Contracts

## Current Issue
- LLM call takes 77 seconds total
- Azure reports 67.4s generation time (10.73 tokens/sec for 723 tokens)
- 10-second overhead for network/serialization
- User waits entire 77s before seeing ANY response

## Streaming Solution Benefits
- First token arrives in ~10-15 seconds
- Response appears progressively as generated
- Same 77s total time, but perceived as 5-10x faster
- Professional, modern UX matching ChatGPT experience

## Backend Changes (web_app.py)

### 1. Add Server-Sent Events (SSE) endpoint

```python
from fastapi.responses import StreamingResponse

@app.post("/api/query_contracts_stream")
async def query_contracts_stream(request: Request):
    """Stream LLM response as Server-Sent Events"""
    import time
    t1 = time.perf_counter()

    print(f"\n{'='*80}")
    print(f"[TIMING] 🚀 Query Contracts STREAMING Request Started")
    print(f"{'='*80}")

    async def generate_stream():
        """Generator function for SSE streaming"""
        try:
            body = await request.json()
            question = body.get("question", "")
            contract_ids = body.get("contract_ids", [])

            print(f"[TIMING] Question: {question[:100]}...")
            print(f"[TIMING] Contract IDs: {len(contract_ids)} contracts")

            # Send initial metadata event
            yield f"event: metadata\ndata: {json.dumps({'contracts_count': len(contract_ids), 'question': question})}\n\n"

            # ... existing contract retrieval code ...
            # (Copy from current implementation up to client creation)

            # Create streaming client
            print(f"[TIMING] Creating async Azure OpenAI client for streaming...")
            async_client = AsyncAzureOpenAI(
                azure_endpoint=ai_svc.aoai_endpoint,
                api_key=ai_svc.aoai_api_key,
                api_version=ai_svc.aoai_version,
            )

            print(f"[TIMING] Starting LLM streaming call...")
            llm_start = time.perf_counter()
            first_token_received = False

            # Stream the response
            stream = await async_client.chat.completions.create(
                model=ai_svc.completions_deployment,
                temperature=ConfigService.get_completion_temperature(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4000,
                stream=True  # Enable streaming
            )

            full_response = ""
            async for chunk in stream:
                if not first_token_received:
                    first_token_time = time.perf_counter() - llm_start
                    print(f"[TIMING] ⚡ First token received in {first_token_time:.2f}s")
                    first_token_received = True

                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_response += content
                        # Send content chunk as SSE
                        yield f"data: {json.dumps({'content': content})}\n\n"

            llm_end = time.perf_counter()
            llm_elapsed = llm_end - llm_start
            print(f"[TIMING] ✅ LLM streaming completed in {llm_elapsed:.2f}s")

            # Send completion event
            t2 = time.perf_counter()
            total_elapsed = t2 - t1
            yield f"event: complete\ndata: {json.dumps({'elapsed': total_elapsed, 'llm_time': llm_elapsed})}\n\n"

            await async_client.close()

        except Exception as e:
            print(f"[ERROR] Streaming error: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

## Frontend Changes (Angular)

### 1. Update contract.service.ts

```typescript
queryContractsStreaming(question: string, contractIds: string[]): Observable<{
  type: 'metadata' | 'content' | 'complete' | 'error',
  data: any
}> {
  return new Observable(observer => {
    const eventSource = new EventSource(
      `${this.apiUrl}/api/query_contracts_stream`,
      {
        // For POST requests, we need to use fetch with SSE
      }
    );

    // Alternative: Use fetchEventSource for POST support
    fetch(`${this.apiUrl}/api/query_contracts_stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question,
        contract_ids: contractIds
      })
    }).then(response => {
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      const readStream = () => {
        reader.read().then(({ done, value }) => {
          if (done) {
            observer.complete();
            return;
          }

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.substring(6));
              observer.next({ type: 'content', data });
            } else if (line.startsWith('event: ')) {
              const eventType = line.substring(7);
              // Next line should be data
            }
          }

          readStream();
        });
      };

      readStream();
    }).catch(error => {
      observer.error(error);
    });

    return () => {
      // Cleanup
    };
  });
}
```

### 2. Update contract-workbench.ts

```typescript
streamingAnswer: string = '';
isStreaming: boolean = false;

askQuestionStreaming(): void {
  if (!this.questionText.trim()) {
    return;
  }

  this.isStreaming = true;
  this.streamingAnswer = '';
  this.questionAnswer = null;

  const contractIds = this.selectedContracts.map(c => c.id);

  this.contractService.queryContractsStreaming(
    this.questionText,
    contractIds
  ).subscribe({
    next: (event) => {
      if (event.type === 'content') {
        // Append new content as it arrives
        this.streamingAnswer += event.data.content;
      } else if (event.type === 'complete') {
        this.isStreaming = false;
        this.questionAnswer = {
          answer: this.streamingAnswer,
          elapsed: event.data.elapsed,
          // ... other fields
        };
      }
    },
    error: (err) => {
      this.isStreaming = false;
      this.error = 'Error streaming response';
      console.error(err);
    }
  });
}
```

### 3. Update contract-workbench.html

```html
<!-- Show streaming content as it arrives -->
<div *ngIf="isStreaming" class="streaming-response">
  <div class="streaming-indicator">
    <div class="spinner"></div>
    <span>Generating response...</span>
  </div>
  <div class="streaming-content" [innerHTML]="streamingAnswer | markdown"></div>
</div>

<!-- Show final response when complete -->
<div *ngIf="questionAnswer && !isStreaming" class="final-response">
  <div [innerHTML]="questionAnswer.answer | markdown"></div>
</div>
```

## Implementation Phases

### Phase 1: Add Detailed Timing (DONE)
✅ Client creation timing
✅ LLM call timing
✅ Content extraction timing
✅ Client close timing

### Phase 2: Analyze Timing Results
- Run with new timing
- Identify where the 10-second overhead occurs
- Determine if it's acceptable or needs optimization

### Phase 3: Implement Streaming (Recommended)
- Add streaming endpoint to backend
- Update Angular service for SSE consumption
- Update UI to show progressive response
- Test with real contracts

### Phase 4: Optimization (If Needed)
- Connection pooling/reuse
- Reduce request payload size
- Optimize prompt construction
- Consider caching common patterns

## Performance Comparison

### Current Non-Streaming:
```
[0s]    User clicks "Ask Question"
[77s]   Response appears
        ❌ User stares at loading spinner for 77 seconds
```

### With Streaming:
```
[0s]    User clicks "Ask Question"
[10s]   First words appear: "Based on the analysis of..."
[12s]   More content: "## Contract Analysis\n\n### Contract 1..."
[45s]   Half the response visible and readable
[77s]   Complete response shown
        ✅ User engaged throughout, can read early content
```

## Effort Estimate
- **Backend SSE endpoint**: 2-3 hours
- **Frontend streaming consumer**: 2-3 hours
- **UI updates**: 1-2 hours
- **Testing**: 2-3 hours
- **Total**: 7-11 hours

## Alternative: Quick Win Without Streaming

If streaming is too complex right now, consider:

1. **Show Progress Indicators**: Update UI every 10 seconds with status
2. **Background Processing**: Return immediately, process async, poll for results
3. **Chunked Processing**: Break into smaller contract batches, show incremental results

But streaming is the best UX and aligns with modern AI application expectations.
