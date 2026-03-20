#!/usr/bin/env bash
# belam — Unified CLI for the workspace: pipelines, primitives, memory, experiments
# Works from anywhere. All paths resolve to the workspace root.

set -euo pipefail

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
SCRIPTS="$WORKSPACE/scripts"
PIPELINES_DIR="$WORKSPACE/pipelines"

# ── Colors ────────────────────────────────────────────────────────────────────
B='\033[1m'    D='\033[2m'    R='\033[0m'
C='\033[36m'   G='\033[32m'   Y='\033[33m'   M='\033[35m'   RD='\033[31m'

usage() {
    printf "${B}belam${R} — Workspace CLI 🔮\n"
    printf "\n${B}PIPELINES${R}\n"
    printf "  ${C}belam pipelines${R}                         List all pipelines\n"
    printf "  ${C}belam pipeline <ver>${R}                    Detail view for one pipeline\n"
    printf "  ${C}belam pipeline <ver> --watch [sec]${R}      Live auto-refresh\n"
    printf "  ${C}belam pipeline update <ver> <args...>${R}   Update pipeline stage\n"
    printf "  ${C}belam orchestrate <ver> <action> <args>${R}  Orchestrated stage transition (auto-handoff)\n"
    printf "  ${C}belam handoffs${R}                          Check for stuck handoffs\n"
    printf "  ${C}belam kickoff <ver>${R}                     Kick off a created pipeline (wake architect)\n"
    printf "  ${C}belam revise <ver> --context \"...\"${R}     Trigger Phase 1 revision cycle (coordinator-initiated)\n"
    printf "  ${C}belam queue-revision <ver> [opts]${R}       Queue a revision request for autorun pickup\n"
    printf "  ${C}belam autorun [--dry-run]${R}               Auto-kick gated/stalled/revision pipelines\n"
    printf "  ${C}belam cleanup [--execute] [--hours N]${R}   Kill stale agent sessions (default: dry run, 24h)\n"
    printf "  ${C}belam pipeline launch <ver> <args...>${R}   Create a new pipeline\n"
    printf "  ${C}belam pipeline analyze <ver> <args...>${R}  Launch analysis pipeline\n"
    printf "\n${B}PRIMITIVES${R}\n"
    printf "  ${C}belam tasks${R}                             List open tasks\n"
    printf "  ${C}belam task <name>${R}                       Show a task (fuzzy match)\n"
    printf "  ${C}belam lessons${R}                           List lessons\n"
    printf "  ${C}belam lesson <name>${R}                     Show a lesson\n"
    printf "  ${C}belam decisions${R}                         List decisions\n"
    printf "  ${C}belam decision <name>${R}                   Show a decision\n"
    printf "  ${C}belam projects${R}                          List projects\n"
    printf "  ${C}belam project <name>${R}                    Show a project\n"
    printf "\n${B}CREATE${R}\n"
    printf "  ${C}belam create lesson \"Title\" [--tags x,y] [--confidence high] [--project name]${R}\n"
    printf "  ${C}belam create decision \"Title\" [--tags x,y] [--skill name] [--project name]${R}\n"
    printf "  ${C}belam create task \"Title\" [--tags x,y] [--priority critical] [--depends x,y] [--project name]${R}\n"
    printf "  ${C}belam create project \"Title\" [--tags x,y] [--status active]${R}\n"
    printf "  ${C}belam create skill \"name\" [--tags x,y] [--desc \"description\"]${R}\n"
    printf "  ${C}belam create command \"name\" [--command \"belam x\"] [--aliases \"belam y\"] [--category cat] [--desc \"...\"]${R}\n"
    printf "  ${D}Shortcuts: c, new${R}\n"
    printf "\n${B}EDIT${R}\n"
    printf "  ${C}belam edit <type/file.md>${R}               Open / view a primitive\n"
    printf "  ${C}belam edit <name> --set key=value${R}       Fuzzy match + update frontmatter field(s)\n"
    printf "  ${D}Shortcut: e${R}\n"
    printf "\n${B}AGENTS${R}\n"
    printf "  ${C}belam agents${R}                            Show active agent roster\n"
    printf "  ${C}belam agent <name>${R}                      Show agent roster (filtered view)\n"
    printf "  ${D}Shortcut: ag${R}\n"
    printf "\n${B}EXPERIMENTS${R}\n"
    printf "  ${C}belam run <ver>${R}                         Run experiments locally for a pipeline\n"
    printf "  ${C}belam run <ver> --analyze-local${R}         Run experiments → chain into analysis loop\n"
    printf "  ${C}belam run <ver> --dry-run${R}               Quick validation run\n"
    printf "  ${C}belam run <ver> --no-recovery${R}           Skip builder agent on errors\n"
    printf "  ${C}belam analyze <ver>${R}                     Run experiment analysis (auto-finds pipeline)\n"
    printf "  ${C}belam analyze --detect${R}                  Auto-detect new experiment results\n"
    printf "  ${C}belam analyze --check-gate <ver>${R}        Check Phase 3 gate\n"
    printf "  ${C}belam analyze-local <ver>${R}               Orchestrated local analysis (architect→critic→builder loop)\n"
    printf "  ${C}belam analyze-local <ver> --dry-run${R}     Preview without kicking agents\n"
    printf "  ${C}belam report <ver>${R}                      Build LaTeX→PDF report (orchestrated)\n"
    printf "\n${B}MEMORY${R}\n"
    printf "  ${C}belam log <message>${R}                     Quick memory log entry\n"
    printf "  ${C}belam log -t <tag> <message>${R}            Tagged memory entry\n"
    printf "  ${C}belam consolidate${R}                       Run memory consolidation\n"
    printf "  ${C}belam consolidate --all-agents${R}          Consolidate all agent memories\n"
    printf "\n${B}NOTEBOOKS${R}\n"
    printf "  ${C}belam build <ver>${R}                       Build a notebook\n"
    printf "  ${C}belam notebooks${R}                         List notebooks\n"
    printf "\n${B}OTHER${R}\n"
    printf "  ${C}belam conversations [--since N]${R}         Export agent conversations (last N hours)\n"
    printf "  ${C}belam knowledge-sync${R}                    Run weekly knowledge sync\n"
    printf "  ${C}belam sync${R}                              Sync workspace → knowledge-repo (dry run)\n"
    printf "  ${C}belam sync --apply${R}                      Sync workspace → knowledge-repo (apply)\n"
    printf "  ${C}belam status${R}                            Quick overview of everything\n"
    printf "  ${C}belam audit [--fix] [--verbose] [--check X]${R}  Audit primitive consistency\n"
    printf "\n${B}SHORTCUTS${R}  ${D}pl pipes t l d pj p s a al nb conv ks cons c e ag au${R}\n"
    echo
    exit 0
}

# ── Helpers ───────────────────────────────────────────────────────────────────

list_primitives() {
    dir="$WORKSPACE/$1"
    type_name="$2"
    if [ ! -d "$dir" ]; then
        echo "  No $type_name directory found."
        return
    fi
    count=$(ls "$dir"/*.md 2>/dev/null | wc -l)
    if [ "$count" -eq 0 ]; then
        echo "  No ${type_name}s found."
        return
    fi
    printf "\n${B}  %-40s %-15s %s${R}\n" "Name" "Status" "Tags"
    printf "  %s\n" "────────────────────────────────────────────────────────────────"
    for f in "$dir"/*.md; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .md)
        status=$(grep -m1 '^status:' "$f" 2>/dev/null | sed 's/^status:\s*//' || echo "—")
        tags=$(grep -m1 '^tags:' "$f" 2>/dev/null | sed 's/^tags:\s*//' || echo "")
        sc="$R"
        case "$status" in
            *open*|*active*|*running*) sc="$G" ;;
            *blocked*)                 sc="$Y" ;;
            *complete*|*done*|*closed*) sc="$D" ;;
        esac
        printf "  %-40s ${sc}%-15s${R} ${D}%s${R}\n" "$name" "$status" "$tags"
    done
    echo
}

show_primitive() {
    dir="$WORKSPACE/$1"
    name="$2"
    file="$dir/$name.md"
    if [ ! -f "$file" ]; then
        file=$(ls "$dir"/*"$name"*.md 2>/dev/null | head -1)
    fi
    if [ -z "$file" ] || [ ! -f "$file" ]; then
        echo "  ❌ Not found: $name in $1/"
        echo "  Available: $(ls "$dir"/*.md 2>/dev/null | xargs -I{} basename {} .md | tr '\n' ', ')"
        return 1
    fi
    cat "$file"
}

# Find the analysis pipeline for a version. Checks for:
#   <ver>-deep-analysis, <ver>-analysis, <ver> (with analysis tags)
# Returns the pipeline version string or empty.
find_analysis_pipeline() {
    ver="$1"
    # Priority order: deep-analysis, analysis, bare version with analysis tag
    for candidate in "${ver}-deep-analysis" "${ver}-analysis"; do
        if [ -f "$PIPELINES_DIR/${candidate}.md" ]; then
            echo "$candidate"
            return
        fi
    done
    # Check if the bare version has analysis-related tags
    if [ -f "$PIPELINES_DIR/${ver}.md" ]; then
        if grep -q 'tags:.*analysis' "$PIPELINES_DIR/${ver}.md" 2>/dev/null; then
            echo "$ver"
            return
        fi
    fi
    # No analysis pipeline found
    echo ""
}

# List all analysis pipelines for a version
list_analysis_pipelines() {
    ver="$1"
    found=()
    for f in "$PIPELINES_DIR"/${ver}*analysis*.md "$PIPELINES_DIR"/${ver}.md; do
        [ -f "$f" ] || continue
        pver=$(basename "$f" .md)
        if grep -q 'tags:.*analysis' "$f" 2>/dev/null || [[ "$pver" == *analysis* ]]; then
            found+=("$pver")
        fi
    done
    # Deduplicate
    printf '%s\n' "${found[@]}" | sort -u
}

# ── Command dispatch ──────────────────────────────────────────────────────────

# ── Codex Engine (primary interface) ──────────────────────────────────────────
# Route through the Codex Engine first. It handles:
#   - No args → supermap (R0)
#   - Coordinate patterns (t1, p5, d2, m3, t1-t3, etc.)
#   - Flags: -e (edit), -n (create), -z (undo), -g (graph), -x (execute)
# Exit code 2 = not handled, fall through to legacy dispatch.
# --raw bypasses both engines entirely.

if [[ "${*}" != *"--raw"* ]] && [[ "${*}" != *"--plain"* ]]; then
    _ce_rc=0
    python3 "$SCRIPTS/codex_engine.py" "$@" || _ce_rc=$?
    if [ "$_ce_rc" -eq 0 ]; then
        exit 0
    fi
    # Exit code 2 = not handled by Codex Engine, try index engine
    if [ "$_ce_rc" -ne 2 ]; then
        exit "$_ce_rc"
    fi

    # Fall through to legacy index engine
    _idx_rc=0
    python3 "$SCRIPTS/belam_index.py" "$@" || _idx_rc=$?
    if [ "$_idx_rc" -eq 0 ]; then
        exit 0
    fi
    if [ "$_idx_rc" -ne 2 ]; then
        exit "$_idx_rc"
    fi
fi

# Strip --raw/--plain for normal dispatch
set -- $(echo "$@" | sed 's/--raw//g; s/--plain//g' | xargs)

case "${1:-help}" in

    # ── Pipelines ─────────────────────────────────────────────────────────────
    pipelines|pipes|pl)
        python3 "$SCRIPTS/pipeline_dashboard.py" "${@:2}"
        ;;

    orchestrate|orch|o)
        python3 "$SCRIPTS/pipeline_orchestrate.py" "${@:2}"
        ;;

    kickoff|kick|ko)
        if [ -z "${2:-}" ]; then
            echo "Usage: belam kickoff <version> [--phase2 [--direction <file>]]"
            echo "Kicks off a created pipeline by waking the architect."
            echo ""
            echo "  --phase2               Approve Phase 2 (human gate at local_analysis_complete)"
            echo "  --direction <file>     Attach Shael's direction file for Phase 2 context"
            exit 1
        fi
        # Pass everything after version to the orchestrator's kickoff handler
        python3 "$SCRIPTS/pipeline_orchestrate.py" kickoff "${@:2}"
        ;;

    revise|rev)
        if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
            echo "Usage: belam revise <version> --context \"revision directions...\""
            echo "  Optional: --revision <num>  (auto-increments if omitted)"
            echo ""
            echo "Triggers a Phase 1 revision cycle: architect→critic→builder→phase1_complete"
            echo "Pipeline must be at phase1_complete."
            exit 1
        fi
        python3 "$SCRIPTS/pipeline_orchestrate.py" "$2" revise "${@:3}"
        ;;

    queue-revision|qr)
        if [ -z "${2:-}" ]; then
            echo "Usage: belam queue-revision <version> [--context-file <path>] [--section \"## Header\"] [--priority critical|high|normal] [--body \"extra context\"]"
            echo ""
            echo "Queues a revision request for autorun pickup. The next heartbeat/autorun cycle"
            echo "will pick it up and kick the revision autonomously."
            echo ""
            echo "Examples:"
            echo "  belam queue-revision build-eq --context-file research/v4_deep_analysis_findings.md --section '## For BUILD-EQUILIBRIUM-SNN' --priority critical"
            echo "  belam queue-revision stack-sp --priority high --body 'Revise stacking to add aliveness checks'"
            exit 1
        fi
        python3 "$SCRIPTS/create_revision_request.py" "${@:2}"
        ;;

    autorun|auto|ar)
        python3 "$SCRIPTS/pipeline_autorun.py" "${@:2}"
        ;;

    cleanup|clean)
        python3 "$SCRIPTS/cleanup_stale_sessions.py" "${@:2}"
        ;;

    handoffs|ho)
        python3 "$SCRIPTS/pipeline_orchestrate.py" --check-pending
        ;;

    automate|auto)
        python3 "$SCRIPTS/pipeline_automate.py" "${@:2}"
        ;;

    pipeline|pipe|p)
        case "${2:-}" in
            update|u)
                python3 "$SCRIPTS/pipeline_update.py" "${@:3}"
                ;;
            orchestrate|orch|o)
                python3 "$SCRIPTS/pipeline_orchestrate.py" "${@:3}"
                ;;
            launch|new|create)
                python3 "$SCRIPTS/launch_pipeline.py" "${@:3}"
                ;;
            analyze|analysis)
                python3 "$SCRIPTS/launch_analysis_pipeline.py" "${@:3}"
                ;;
            "")
                echo "Usage: belam pipeline <version>  or  belam pipeline update|launch|analyze <args...>"
                ;;
            *)
                python3 "$SCRIPTS/pipeline_dashboard.py" "${@:2}"
                ;;
        esac
        ;;

    # ── Link relationships ────────────────────────────────────────────────────
    link|ln)
        python3 "$SCRIPTS/belam_index.py" "$@"
        ;;

    # ── Primitives ────────────────────────────────────────────────────────────
    tasks|t)
        list_primitives "tasks" "task"
        ;;
    task)
        show_primitive "tasks" "${2:?Usage: belam task <name>}"
        ;;

    lessons|l)
        list_primitives "lessons" "lesson"
        ;;
    lesson)
        show_primitive "lessons" "${2:?Usage: belam lesson <name>}"
        ;;

    decisions|d)
        list_primitives "decisions" "decision"
        ;;
    decision)
        show_primitive "decisions" "${2:?Usage: belam decision <name>}"
        ;;

    projects|pj)
        list_primitives "projects" "project"
        ;;
    project)
        show_primitive "projects" "${2:?Usage: belam project <name>}"
        ;;

    # ── Create primitives ─────────────────────────────────────────────────────
    create|new|c)
        shift
        python3 "$SCRIPTS/create_primitive.py" "$@"
        ;;

    # ── Edit primitives ───────────────────────────────────────────────────────
    edit|e)
        shift
        python3 "$SCRIPTS/edit_primitive.py" "$@"
        ;;

    # ── Agent roster ──────────────────────────────────────────────────────────
    agents|agent|ag)
        show_primitive "projects" "agent-roster"
        ;;

    # ── Experiments ──────────────────────────────────────────────────────────
    run|r)
        if [ -z "${2:-}" ]; then
            echo "Usage: belam run <version> [--dry-run] [--workers N] [--max-retries N] [--no-recovery]"
            echo ""
            echo "Run experiments locally for a pipeline. Auto-updates pipeline stages."
            echo "Builder agent is automatically invoked if errors occur (disable with --no-recovery)."
            exit 1
        fi
        python3 "$SCRIPTS/pipeline_orchestrate.py" "$2" run-experiment "${@:3}"
        ;;

    # ── Local Analysis ───────────────────────────────────────────────────────
    analyze-local|al)
        if [ -z "${2:-}" ]; then
            echo "Usage: belam analyze-local <version> [--dry-run]"
            echo ""
            echo "Orchestrated local analysis pipeline. Runs data prep, then kicks"
            echo "architect→critic→builder→critic loop with reasoning enabled."
            echo "After code review passes, auto-builds LaTeX→PDF report."
            exit 1
        fi
        python3 "$SCRIPTS/pipeline_orchestrate.py" "$2" local-analysis "${@:3}"
        ;;

    # ── Report Builder ────────────────────────────────────────────────────────
    report)
        if [ -z "${2:-}" ]; then
            echo "Usage: belam report <version>"
            echo ""
            echo "Build LaTeX report from approved analysis (orchestrated)."
            exit 1
        fi
        python3 "$SCRIPTS/pipeline_orchestrate.py" "$2" report-build "${@:3}"
        ;;

    # ── Analysis ──────────────────────────────────────────────────────────────
    analyze|a)
        shift
        if [ "${1:-}" = "--detect" ]; then
            python3 "$SCRIPTS/analyze_experiment.py" --detect "${@:2}"
        elif [ "${1:-}" = "--check-gate" ]; then
            python3 "$SCRIPTS/analyze_experiment.py" --check-gate "${@:2}"
        elif [ -n "${1:-}" ]; then
            ver="$1"; shift

            # Auto-find the analysis pipeline for this version
            analysis_pipe=$(find_analysis_pipeline "$ver")

            if [ -n "$analysis_pipe" ]; then
                printf "${D}  Found analysis pipeline: ${R}${C}${analysis_pipe}${R}\n"
                # Show its current status
                status=$(grep -m1 '^status:' "$PIPELINES_DIR/${analysis_pipe}.md" 2>/dev/null | sed 's/^status:\s*//' || echo "unknown")
                case "$status" in
                    *complete*) printf "  Status: ${G}${status}${R}\n" ;;
                    *blocked*)  printf "  Status: ${Y}${status}${R}\n" ;;
                    *)          printf "  Status: ${C}${status}${R}\n" ;;
                esac
                echo

                # Check if there are multiple analysis pipelines
                all_pipes=$(list_analysis_pipelines "$ver")
                pipe_count=$(echo "$all_pipes" | wc -l)
                if [ "$pipe_count" -gt 1 ]; then
                    printf "${D}  Multiple analysis pipelines found for ${ver}:${R}\n"
                    echo "$all_pipes" | while read -r pv; do
                        ps=$(grep -m1 '^status:' "$PIPELINES_DIR/${pv}.md" 2>/dev/null | sed 's/^status:\s*//' || echo "?")
                        printf "    ${C}%-30s${R} %s\n" "$pv" "$ps"
                    done
                    echo
                fi
            else
                printf "${D}  No analysis pipeline found for ${ver} — running raw analysis${R}\n"
            fi

            # Run the analysis script
            python3 "$SCRIPTS/analyze_experiment.py" --notebook "$ver" "$@"
        else
            echo "Usage: belam analyze <version>  |  belam analyze --detect  |  belam analyze --check-gate <ver>"
        fi
        ;;

    # ── Memory ────────────────────────────────────────────────────────────────
    log)
        shift
        if [ "${1:-}" = "-t" ]; then
            tag="$2"; shift 2
            python3 "$SCRIPTS/log_memory.py" --tags "$tag" "$*"
        else
            python3 "$SCRIPTS/log_memory.py" "$*"
        fi
        ;;

    consolidate|cons)
        shift
        python3 "$SCRIPTS/consolidate_memories.py" "$@"
        python3 "$SCRIPTS/embed_primitives.py"
        python3 "$SCRIPTS/codex_engine.py" --boot
        ;;

    embed-primitives|ep)
        shift
        python3 "$SCRIPTS/embed_primitives.py" "$@"
        python3 "$SCRIPTS/codex_engine.py" --boot
        ;;

    boot)
        python3 "$SCRIPTS/codex_engine.py" --boot
        ;;

    # ── Audit primitives ──────────────────────────────────────────────────────
    audit|au)
        shift
        python3 "$SCRIPTS/audit_primitives.py" "$@"
        ;;

    # ── Notebooks ─────────────────────────────────────────────────────────────
    build)
        python3 "$SCRIPTS/build_notebook.py" "${@:2}"
        ;;

    notebooks|nb)
        echo
        printf "${B}  Notebooks${R}\n"
        printf "  %s\n" "────────────────────────────────────────────────────────────────"
        for f in "$WORKSPACE"/SNN_research/machinelearning/snn_applied_finance/notebooks/*.ipynb; do
            [ -f "$f" ] || continue
            local_name=$(basename "$f")
            size=$(du -h "$f" | cut -f1)
            modified=$(stat -c '%y' "$f" 2>/dev/null | cut -d. -f1 || stat -f '%Sm' "$f" 2>/dev/null)
            printf "  %-50s ${D}%s  %s${R}\n" "$local_name" "$size" "$modified"
        done
        echo
        ;;

    # ── Other ─────────────────────────────────────────────────────────────────
    conversations|conv)
        shift
        python3 "$SCRIPTS/export_agent_conversations.py" "$@"
        ;;

    knowledge-sync|ks)
        shift
        python3 "$SCRIPTS/weekly_knowledge_sync.py" "$@"
        ;;

    sync)
        shift
        python3 "$SCRIPTS/sync_knowledge_repo.py" "$@"
        ;;

    # ── Status (quick overview) ───────────────────────────────────────────────
    status|s)
        echo
        printf "${B}═══════════════════════════════════════════════════════════════${R}\n"
        printf "${B}  🔮 WORKSPACE STATUS${R}\n"
        printf "${B}═══════════════════════════════════════════════════════════════${R}\n"

        # Pipelines
        printf "\n${B}  📋 Pipelines${R}\n"
        python3 "$SCRIPTS/launch_pipeline.py" --list 2>/dev/null | tail -n +1

        # Open tasks
        printf "\n${B}  📌 Open Tasks${R}\n"
        found=0
        for f in "$WORKSPACE"/tasks/*.md; do
            [ -f "$f" ] || continue
            if grep -q 'status:.*open\|status:.*blocked' "$f" 2>/dev/null; then
                name=$(basename "$f" .md)
                status=$(grep -m1 '^status:' "$f" | sed 's/^status:\s*//')
                sc="$G"
                [[ "$status" == *blocked* ]] && sc="$Y"
                printf "  ${sc}%-12s${R} %s\n" "$status" "$name"
                found=1
            fi
        done
        [ "$found" = 0 ] && printf "  ${D}(none)${R}\n"

        # Today's memory count
        today=$(date -u +%Y-%m-%d)
        mem_file="$WORKSPACE/memory/$today.md"
        if [ -f "$mem_file" ]; then
            entries=$(grep -c '^## ' "$mem_file" 2>/dev/null || echo 0)
            printf "\n${B}  🧠 Today's Memory${R}\n"
            printf "  %s entries in memory/%s.md\n" "$entries" "$today"
        fi

        # Git status
        printf "\n${B}  📂 Git${R}\n"
        cd "$WORKSPACE/SNN_research/machinelearning" 2>/dev/null && \
            changes=$(git status --short 2>/dev/null | wc -l) && \
            printf "  machinelearning: %s uncommitted files\n" "$changes"
        cd "$WORKSPACE" 2>/dev/null && \
            changes=$(git status --short 2>/dev/null | wc -l) && \
            printf "  workspace: %s uncommitted files\n" "$changes"

        echo
        ;;

    transcribe|tr)
        if [ -z "${2:-}" ]; then
            echo "Usage: belam transcribe <audio_file> [--model small] [--json]"
            exit 1
        fi
        python3 "$SCRIPTS/transcribe_audio.py" "${@:2}"
        ;;

    # ── Memory extraction ─────────────────────────────────────────────────────
    extract|ex)
        bash "$SCRIPTS/belam_extract.sh" "${@:2}"
        ;;

    # ── Edge checker ──────────────────────────────────────────────────────────
    edges|eg)
        python3 "$SCRIPTS/codex_engine.py" edges "${@:2}"
        ;;

    help|-h|--help)
        usage
        ;;

    *)
        echo "Unknown command: $1"
        echo "Run 'belam help' for usage."
        exit 1
        ;;
esac
