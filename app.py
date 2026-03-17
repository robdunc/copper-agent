import os
import sys
import json
import argparse
from datetime import datetime

from flask import Flask, render_template, Response, stream_with_context
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SYSTEM_PROMPT = """You are a senior copper market analyst at a top-tier commodities trading firm.
You provide authoritative, data-driven daily market intelligence briefings to institutional clients.
Your analysis is precise, actionable, and grounded in real market dynamics."""

BRIEFING_PROMPT = f"""Generate a comprehensive copper market daily briefing for {datetime.now().strftime("%A, %B %d, %Y")}.

Structure your report with the following sections:

## Price Trends
- LME copper spot price context and recent direction
- Week-over-week and month-over-month performance summary
- Key technical support and resistance levels
- COMEX and SHFE price comparisons

## Supply & Demand Factors
- Major mining output (Chile, Peru, DRC, China)
- Smelter/refinery capacity and utilization rates
- Chinese demand signals (property sector, manufacturing PMI)
- Global exchange inventory levels (LME, COMEX, SHFE)
- Scrap copper availability and premiums

## Key Market Insights
- Macroeconomic drivers (USD index, interest rate expectations, China stimulus)
- Geopolitical risks affecting supply chains
- Energy transition demand tailwinds (EVs, grid infrastructure, data centers)
- Notable transactions or contract activity

## Market Sentiment & Outlook
- Current speculative positioning (COT data context)
- Short-term price outlook for the next 1–2 weeks
- Key upside and downside risks
- Events to watch (economic data releases, mine updates, policy decisions)

Write in a professional, direct style. Use specific figures and ranges where appropriate.
End with a one-sentence bottom line for traders."""


def create_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def stream_briefing():
    """Yield text chunks from the Claude streaming response."""
    client = create_client()
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": BRIEFING_PROMPT}],
    ) as stream:
        for text in stream.text_stream:
            yield text


# ── Web routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    def sse_generator():
        try:
            for chunk in stream_briefing():
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'error': 'Invalid API key. Check your ANTHROPIC_API_KEY.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Unexpected error: {str(e)}'})}\n\n"

    return Response(
        stream_with_context(sse_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── CLI mode ─────────────────────────────────────────────────────────────────

def run_cli():
    print("\n\033[33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print("\033[33m  🔶 COPPER MARKET INTELLIGENCE BRIEFING\033[0m")
    print(f"\033[33m  {datetime.now().strftime('%A, %B %d, %Y  %H:%M %Z')}\033[0m")
    print("\033[33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")

    try:
        for chunk in stream_briefing():
            print(chunk, end="", flush=True)
        print("\n\n\033[33m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n")
    except ValueError as e:
        print(f"\n\033[31mError: {e}\033[0m", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n\033[90m(interrupted)\033[0m")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Copper Market Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python app.py          # start web server\n  python app.py --cli    # print briefing to terminal",
    )
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no web server)")
    parser.add_argument("--port", type=int, default=5000, help="Web server port (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Web server host (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        print("\033[33m🔶 Copper Market Intelligence Agent\033[0m")
        print(f"   Listening on http://localhost:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
