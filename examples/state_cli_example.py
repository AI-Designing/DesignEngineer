#!/usr/bin/env python3
"""
Command Line Interface for FreeCAD State Management

This CLI provides easy access to state management functionality.
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_designer.services.state_service import FreeCADStateService


def setup_argument_parser():
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description="FreeCAD State Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze --document "MyProject" --session "session1"
  %(prog)s get-state --document "MyProject"
  %(prog)s monitor --document "MyProject" --conditions '{"Pad Created": true}'
  %(prog)s list-states --document "MyProject"
  %(prog)s export --document "MyProject" --output analysis.json
        """,
    )

    # Redis connection options
    parser.add_argument(
        "--redis-host",
        default="localhost",
        help="Redis server host (default: localhost)",
    )
    parser.add_argument(
        "--redis-port", type=int, default=6379, help="Redis server port (default: 6379)"
    )
    parser.add_argument(
        "--redis-db", type=int, default=0, help="Redis database number (default: 0)"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze FreeCAD state and cache results"
    )
    analyze_parser.add_argument("--document", help="Document name for key generation")
    analyze_parser.add_argument("--session", help="Session ID")
    analyze_parser.add_argument("--doc-path", help="Path to FreeCAD document file")
    analyze_parser.add_argument(
        "--expiration",
        type=int,
        default=3600,
        help="Cache expiration time in seconds (default: 3600)",
    )

    # Get state command
    state_parser = subparsers.add_parser("get-state", help="Get current state")
    state_parser.add_argument("--document", help="Document name")
    state_parser.add_argument("--session", help="Session ID")
    state_parser.add_argument("--key", help="Specific state key to retrieve")

    # Get analysis command
    analysis_parser = subparsers.add_parser("get-analysis", help="Get current analysis")
    analysis_parser.add_argument("--document", help="Document name")
    analysis_parser.add_argument("--key", help="Specific analysis key to retrieve")

    # List commands
    list_states_parser = subparsers.add_parser("list-states", help="List cached states")
    list_states_parser.add_argument("--document", help="Filter by document name")
    list_states_parser.add_argument("--session", help="Filter by session ID")

    list_analyses_parser = subparsers.add_parser(
        "list-analyses", help="List cached analyses"
    )
    list_analyses_parser.add_argument("--document", help="Filter by document name")
    list_analyses_parser.add_argument("--type", help="Filter by analysis type")

    # History command
    history_parser = subparsers.add_parser("history", help="Get state history")
    history_parser.add_argument("--document", help="Document name")
    history_parser.add_argument("--session", help="Session ID")
    history_parser.add_argument(
        "--limit", type=int, default=10, help="Number of entries to show"
    )

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor state conditions")
    monitor_parser.add_argument("--document", required=True, help="Document name")
    monitor_parser.add_argument(
        "--conditions",
        required=True,
        help="JSON string of conditions to monitor (e.g., '{\"Pad Created\": true}')",
    )

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two states")
    compare_parser.add_argument("--key1", required=True, help="First state key")
    compare_parser.add_argument("--key2", required=True, help="Second state key")

    # Status command
    subparsers.add_parser("status", help="Get service status")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("--document", help="Document name to export")
    export_parser.add_argument("--output", help="Output file path")
    export_parser.add_argument(
        "--format", choices=["json", "dict"], default="json", help="Export format"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old data")
    cleanup_parser.add_argument(
        "--older-than",
        type=int,
        default=24,
        help="Remove data older than N hours (default: 24)",
    )

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cached data")
    clear_parser.add_argument(
        "--document", help="Document name (if not specified, clears all)"
    )
    clear_parser.add_argument("--states", action="store_true", help="Clear states")
    clear_parser.add_argument("--analyses", action="store_true", help="Clear analyses")
    clear_parser.add_argument("--all", action="store_true", help="Clear all data")

    return parser


def create_service(args):
    """Create and connect to the state service"""
    service = FreeCADStateService(
        redis_host=args.redis_host, redis_port=args.redis_port, redis_db=args.redis_db
    )

    if not service.connect():
        print("❌ Failed to connect to Redis. Make sure Redis server is running.")
        sys.exit(1)

    return service


def handle_analyze(service, args):
    """Handle analyze command"""
    print("🔍 Analyzing FreeCAD state...")

    result = service.analyze_and_cache_state(
        doc_path=args.doc_path,
        document_name=args.document,
        session_id=args.session,
        expiration=args.expiration,
    )

    if result["success"]:
        print("✅ Analysis completed successfully!")
        print(f"Analysis Key: {result['analysis_key']}")
        if result["state_key"]:
            print(f"State Key: {result['state_key']}")

        # Display analysis results
        if "analysis_result" in result and "analysis" in result["analysis_result"]:
            print("\n📋 Analysis Results:")
            analysis = result["analysis_result"]["analysis"]
            for key, value in analysis.items():
                status_icon = "✅" if value else "❌"
                print(f"  {key}: {status_icon}")
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def handle_get_state(service, args):
    """Handle get-state command"""
    if args.key:
        state = service.state_cache.retrieve_state(args.key)
        print(f"State for key '{args.key}':")
    else:
        state = service.get_current_state(args.document, args.session)
        print(f"Current state for document '{args.document}':")

    if state:
        print(json.dumps(state, indent=2))
    else:
        print("No state found")


def handle_get_analysis(service, args):
    """Handle get-analysis command"""
    if args.key:
        analysis = service.state_cache.retrieve_analysis(args.key)
        print(f"Analysis for key '{args.key}':")
    else:
        analysis = service.get_current_analysis(args.document)
        print(f"Current analysis for document '{args.document}':")

    if analysis:
        print(json.dumps(analysis, indent=2))
    else:
        print("No analysis found")


def handle_list_states(service, args):
    """Handle list-states command"""
    keys = service.state_cache.list_states(args.document, args.session)

    if keys:
        print(f"Found {len(keys)} state(s):")
        for key in keys:
            print(f"  {key}")
    else:
        print("No states found")


def handle_list_analyses(service, args):
    """Handle list-analyses command"""
    keys = service.state_cache.list_analyses(args.document, args.type)

    if keys:
        print(f"Found {len(keys)} analysis/analyses:")
        for key in keys:
            print(f"  {key}")
    else:
        print("No analyses found")


def handle_history(service, args):
    """Handle history command"""
    history = service.get_state_history(args.document, args.session, args.limit)

    if history:
        print(f"State history (last {len(history)} entries):")
        for i, entry in enumerate(history):
            metadata = entry.get("metadata", {})
            timestamp = metadata.get("timestamp", "Unknown")
            print(f"  {i+1}. {entry['key']} - {timestamp}")
    else:
        print("No history found")


def handle_monitor(service, args):
    """Handle monitor command"""
    try:
        conditions = json.loads(args.conditions)
    except json.JSONDecodeError:
        print("❌ Invalid JSON format for conditions")
        sys.exit(1)

    print(f"🔍 Monitoring conditions for document '{args.document}':")
    for condition, expected in conditions.items():
        print(f"  {condition}: {expected}")

    result = service.monitor_state_changes(args.document, conditions)

    if result["success"]:
        print(f"\n📊 Monitoring Results:")
        print(
            f"All conditions satisfied: {'✅' if result['all_conditions_satisfied'] else '❌'}"
        )

        for condition, check in result["conditions_met"].items():
            status = "✅" if check["satisfied"] else "❌"
            print(
                f"  {condition}: {status} (Expected: {check['expected']}, Actual: {check['actual']})"
            )
    else:
        print(f"❌ Monitoring failed: {result.get('error', 'Unknown error')}")


def handle_compare(service, args):
    """Handle compare command"""
    comparison = service.compare_states(args.key1, args.key2)

    if "error" in comparison:
        print(f"❌ Comparison failed: {comparison['error']}")
        return

    print(f"🔄 Comparing states:")
    print(f"  Key 1: {args.key1}")
    print(f"  Key 2: {args.key2}")
    print(f"  States equal: {'✅' if comparison['states_equal'] else '❌'}")

    if comparison["differences"]:
        print("\nDifferences:")
        for field, diff in comparison["differences"].items():
            print(f"  {field}: {diff['state1']} → {diff['state2']}")
    else:
        print("\nNo differences found")


def handle_status(service, args):
    """Handle status command"""
    status = service.get_service_status()

    print("📊 Service Status:")
    print(f"  Connected: {'✅' if status['connected'] else '❌'}")
    print(
        f"  Redis: {status['redis_connection']['host']}:{status['redis_connection']['port']}"
    )

    if "cache_summary" in status:
        summary = status["cache_summary"]
        print(f"  Cached States: {summary['total_states']}")
        print(f"  Cached Analyses: {summary['total_analyses']}")
        if summary["documents"]:
            print(f"  Documents: {', '.join(summary['documents'])}")


def handle_export(service, args):
    """Handle export command"""
    data = service.export_data(args.document, args.format)

    if args.output:
        with open(args.output, "w") as f:
            if args.format == "json":
                f.write(data)
            else:
                json.dump(data, f, indent=2)
        print(f"✅ Data exported to {args.output}")
    else:
        if args.format == "json":
            print(data)
        else:
            print(json.dumps(data, indent=2))


def handle_cleanup(service, args):
    """Handle cleanup command"""
    result = service.cleanup_old_data(args.older_than)

    print(f"🧹 Cleanup completed:")
    print(f"  Deleted states: {result['deleted_states']}")
    print(f"  Deleted analyses: {result['deleted_analyses']}")
    print(f"  Cutoff: {result['cutoff_hours']} hours")


def handle_clear(service, args):
    """Handle clear command"""
    if args.all:
        states_cleared = service.state_cache.clear_all_states(args.document)
        analyses_cleared = service.state_cache.clear_all_analyses(args.document)
        print(f"🗑️  Cleared {states_cleared} states and {analyses_cleared} analyses")
    else:
        if args.states:
            cleared = service.state_cache.clear_all_states(args.document)
            print(f"🗑️  Cleared {cleared} states")
        if args.analyses:
            cleared = service.state_cache.clear_all_analyses(args.document)
            print(f"🗑️  Cleared {cleared} analyses")


def main():
    """Main CLI function"""
    parser = setup_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        service = create_service(args)

        # Route to appropriate handler
        if args.command == "analyze":
            handle_analyze(service, args)
        elif args.command == "get-state":
            handle_get_state(service, args)
        elif args.command == "get-analysis":
            handle_get_analysis(service, args)
        elif args.command == "list-states":
            handle_list_states(service, args)
        elif args.command == "list-analyses":
            handle_list_analyses(service, args)
        elif args.command == "history":
            handle_history(service, args)
        elif args.command == "monitor":
            handle_monitor(service, args)
        elif args.command == "compare":
            handle_compare(service, args)
        elif args.command == "status":
            handle_status(service, args)
        elif args.command == "export":
            handle_export(service, args)
        elif args.command == "cleanup":
            handle_cleanup(service, args)
        elif args.command == "clear":
            handle_clear(service, args)
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()

    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
