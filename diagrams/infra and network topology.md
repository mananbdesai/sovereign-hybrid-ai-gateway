flowchart TD
    subgraph Edge_Server ["Physical Edge Server"]
        MetaEdge(Intel i7 - 32GB RAM - No GPU)
        style MetaEdge fill:none,stroke:none,font-weight:bold
        
        subgraph Proxmox ["Proxmox VE Hypervisor"]
            MetaHost(Host IP: 192.168.0.x)
            style MetaHost fill:none,stroke:none
            
            Bridge[Virtual Bridge vmbr0]
            
            subgraph LXC122 ["LXC 122: The Engine"]
                Meta122(IP: 192.168.0.122 - 6GB RAM)
                style Meta122 fill:none,stroke:none
                
                subgraph Docker ["Docker Engine"]
                    subgraph ai_stack ["Docker Compose: ai-stack"]
                        Router[FastAPI Policy Router]
                        Qdrant[(Qdrant Vector DB - Ports 6333, 6334)]
                        Redis[(Redis Cache - Port 6379)]
                    end
                end
                Portainer[Portainer UI - Port 9443]
                
                %% Pin Meta122 to the top
                Meta122 ~~~ Docker
            end

            subgraph LXC121 ["LXC 121: The Brain"]
                Meta121(IP: 192.168.0.121 - 12GB RAM)
                style Meta121 fill:none,stroke:none
                
                Ollama[Ollama Service - Model llama3]
                
                %% Pin Meta121 to the top
                Meta121 ~~~ Ollama
            end
            
            %% Pin MetaHost to the top
            MetaHost ~~~ Bridge
        end
        
        %% Pin MetaEdge to the top
        MetaEdge ~~~ Proxmox
    end

    %% Network Paths
    Dev[Developer Laptop - DHCP] -->|SSH Port 22 Development| LXC122
    Dev -->|HTTPS Port 9443 Management| Portainer
    
    Bridge -.-> LXC122
    Bridge -.-> LXC121

    %% Traffic Routing Paths
    Router -->|Read and Write localhost 6333| Qdrant
    Router -->|Cache Hit or Miss localhost 6379| Redis
    Router ==>|CONFIDENTIAL Traffic HTTP POST 11434| Ollama
    Router -->|PUBLIC Traffic HTTPS| OpenAI([OpenAI API GPT-4o-mini])

    %% Styling Classes
    classDef physical fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef hypervisor fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef container fill:#fff3e0,stroke:#f57c00,stroke-width:2px,stroke-dasharray: 5 5;
    classDef internal fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef external fill:#eceff1,stroke:#607d8b,stroke-width:2px;
    
    class Edge_Server physical;
    class Proxmox hypervisor;
    class LXC121,LXC122 container;
    class Router,Qdrant,Redis,Ollama internal;
    class OpenAI external;