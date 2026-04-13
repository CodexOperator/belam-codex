graph TD
    %% Central core
    COCKPIT[OpenClaw Cockpit V5<br>.md frontmatter = truth<br>Reactive hooks + daemon] 
    --> RENDER[Supermap Render Engine<br>Runtime ASCII / Visual LLM-native map<br>NO JSON • NO raw .md]

    %% Left side - triggers
    HOOKS[Reactive .md Hooks & Daemon<br>post_edit_hooks.py] 
    -->|triggers mine + rebuild on lessons/decisions/logs| COCKPIT

    TEMPLATES[Templates + Supermap Slots<br>compact invoke-only actions] 
    -->|feeds visual explanations| RENDER

    %% Top - Graphify (static)
    GRAPHIFY[Graphify Backend<br>Leiden clusters + multimodal<br>primitives/ + lessons/ + decisions/] 
    -->|default render target| RENDER
    GRAPHIFY <-->|mutual loop: lessons → clusters| MEMPALACE

    %% Right - MemPalace (dynamic)
    MEMPALACE[MemPalace Dynamic KG<br>Wings/Rooms/Halls + temporal triples<br>primitives/ subdirs + daily/weekly logs] 
    -->|chronological decisions + training data| RENDER
    MEMPALACE <-->|auto-ingest chat logs + --extract general| CHATLOGS

    %% Bottom right - training data
    CHATLOGS[Raw Chat Logs + Processed Conversations<br>separate directory → training data] 
    -->|mempalace mine --mode convos --extract general<br>+ quality labels via distillation| MEMPALACE
    CHATLOGS -->|Graphify clusters good/bad + should-do/avoid| GRAPHIFY

    %% Bottom - distillation & handoff
    DISTILL[Your Distillation System<br>lessons → heuristics/frameworks/strategies<br>real-world success tags] 
    -->|writes .md with labels| HOOKS
    DISTILL -->|feeds into both| MEMPALACE
    DISTILL -->|feeds into both| GRAPHIFY

    GIFF[Multi-Agent Giff Handoff<br>visual graph-traversal maps<br>should-do / avoid highlights] 
    -->|token-efficient handoffs| RENDER

    %% Web connections (full mesh)
    GRAPHIFY <-->|bidirectional enrichment| MEMPALACE
    RENDER <-->|pulls fused slice| GRAPHIFY
    RENDER <-->|pulls fused slice| MEMPALACE
    HOOKS <-->|triggers on any .md change| DISTILL

    style COCKPIT fill:#0a2540,stroke:#00ffcc
    style RENDER fill:#001f3f,stroke:#ffcc00,stroke-width:4px
    classDef memory fill:#112233,stroke:#00ccff
    class GRAPHIFY,MEMPALACE,DISTILL,CHATLOGS memory
