flowchart LR
 subgraph subGraph0["CPU Execution Enclave"]
        E["Generate 384-Dim Vectors"]
        D{"HuggingFace Embeddings<br>all-MiniLM-L6-v2"}
  end
    A["Legacy Storage<br>/opt/ai-gateway/data"] -- "Load .cbl & .txt" --> B("LangChain Document Loader")
    B --> C("Recursive Character Text Splitter<br>Chunk: 1000, Overlap: 200")
    C --> D
    D -- Device: CPU Forced --> E
    E -- Upsert via gRPC/HTTP --> F[("Qdrant Vector DB<br>Collection: mainframe_logic")]

     E:::logic
     D:::logic
     B:::logic
     C:::logic
    classDef logic fill:#e3f2fd,stroke:#1565c0,stroke-width:2px