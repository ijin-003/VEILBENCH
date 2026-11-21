"""CLI entry point for a single standalone MPC party process."""

import argparse
import json
import sys

from mpyc.runtime import mpc

from backend.mpc.protocol import run_mpc_summation


def main():
    parser = argparse.ArgumentParser(description="VEILBENCH MPC Party Runner")
    args, _ = parser.parse_known_args()

    try:
        salary = json.loads(sys.stdin.readline())
        result = mpc.run(run_mpc_summation(salary))
        # Print JSON output marker for coordinator parsing
        print(f"__MPC_RESULT_START__{json.dumps(result)}__MPC_RESULT_END__")
        sys.exit(0)
    except Exception as e:
        print(
            f"__MPC_ERROR_START__{json.dumps({'error': str(e), 'type': type(e).__name__})}__MPC_ERROR_END__",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
