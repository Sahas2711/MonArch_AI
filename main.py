# main.py — MonArch AI CLI entrypoint
import argparse


from utils.config import MCP_HOST, MCP_PORT


def main():
    parser = argparse.ArgumentParser(description="MonArch AI — CLI Entrypoint")
    parser.add_argument(
        "--serve-mcp",
        action="store_true",
        help=f"Start the MCP tool server (Streamable-HTTP on port {MCP_PORT})",
    )
    parser.add_argument(
        "--mcp-host",
        default=MCP_HOST,
        help=f"MCP server host (default: {MCP_HOST})",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=MCP_PORT,
        help=f"MCP server port (default: {MCP_PORT})",
    )
    args = parser.parse_args()

    if args.serve_mcp:
        from MCP.server import run_mcp_server

        run_mcp_server(host=args.mcp_host, port=args.mcp_port)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
