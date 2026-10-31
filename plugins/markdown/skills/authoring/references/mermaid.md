# Mermaid Diagram Examples

Rule: architecture with nodes and edges, flows, and anything whose labels contain wide characters go in Mermaid. Quote every node
label and use `<br>` for line breaks.

## Contents

- [flowchart LR: host management](#flowchart-lr-host-management)
- [flowchart TD: deployment flow](#flowchart-td-deployment-flow)
- [flowchart LR: service dependencies](#flowchart-lr-service-dependencies)
- [sequenceDiagram: API call timing](#sequencediagram-api-call-timing)

## Flowchart LR: Host Management

```mermaid
flowchart LR
    subgraph Bootstrap
        B1["bootstrap-host<br>admin@10.0.0.1"]
    end
    subgraph Managed
        M1["managed-host<br>svcuser@10.0.0.1"]
    end
    B1 --> M1
```

## Flowchart TD: Deployment Flow

```mermaid
flowchart TD
    A["Build image"] --> B["Push to registry"]
    B --> C["Pull on target host"]
    C --> D["docker compose up"]
    D --> E{"Health check"}
    E -->|"pass"| F["Done"]
    E -->|"fail"| G["Roll back"]
```

## Flowchart LR: Service Dependencies

```mermaid
flowchart LR
    WEB["Web<br>8080"] --> API["API Server<br>3000"]
    API --> PG[("PostgreSQL<br>5432")]
    API --> REDIS[("Redis<br>6379")]
```

## sequenceDiagram: API Call Timing

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB

    Client->>API: POST /login
    API->>DB: SELECT user WHERE email=?
    DB-->>API: user record
    API-->>Client: 200 OK + token
```

Sequence diagram messages after the `:` are free text and need no quotes.
