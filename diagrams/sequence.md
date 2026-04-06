sequenceDiagram
    autonumber
    actor User as User (UI)
    participant Gateway as FastAPI Router (LXC 122)
    participant Policy as Governance Module
    participant Qdrant as Local Qdrant DB (LXC 122)
    participant Llama as Llama 3 (LXC 121)
    participant OpenAI as OpenAI API (Cloud)

    User->>Gateway: POST /query {prompt, classification}
    Gateway->>Policy: Evaluate ROUTING_POLICY
    
    alt Classification == CONFIDENTIAL
        Policy-->>Gateway: Enforce STRICT_LOCAL
        Gateway->>Qdrant: Query Top-3 COBOL Context (CPU Embeddings)
        Qdrant-->>Gateway: Return Vector Matches
        Gateway->>Llama: Send Prompt + Injected COBOL Context
        Llama-->>Gateway: Return Sovereign Generation
    else Classification == PUBLIC
        Policy-->>Gateway: Allow Public Traverse (FinOps Governed)
        Gateway->>OpenAI: Send Generic Prompt (gpt-4o-mini)
        OpenAI-->>Gateway: Return External Generation
    end
    
    Gateway-->>User: Final Output