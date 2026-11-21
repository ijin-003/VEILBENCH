"""Core MPyC Secure Summation Protocol Implementation."""

import logging
from typing import Any, Dict

from mpyc.runtime import mpc

from backend.mpc.config import PRECISION_BITS
from backend.mpc.exceptions import ConfigurationError
from backend.mpc.validation import validate_salary

logger = logging.getLogger("veilbench.mpc.protocol")


async def run_mpc_summation(my_salary: int) -> Dict[str, Any]:
    """
    Execute the three-party Shamir-based secure summation protocol using MPyC.

    Steps:
    1. Validate input salary within cryptographic domain.
    2. Start the asynchronous MPyC runtime.
    3. Check threshold configuration (t < m / 2 honest majority).
    4. Distribute secret input via Shamir secret sharing (mpc.input).
    5. Perform local homomorphic summation of shares without network rounds.
    6. Reconstruct the aggregate sum across parties (mpc.output).
    7. Compute public average = aggregate_sum / party_count.
    8. Gracefully shut down party runtime and close peer connections.
    """
    validated_salary = validate_salary(my_salary)

    num_parties = len(mpc.parties)
    threshold = mpc.threshold

    if num_parties != 3 or threshold != 1:
        raise ConfigurationError("Exactly three parties and threshold one are required")

    await mpc.start()

    # Verify honest majority
    if threshold >= (num_parties / 2.0):
        await mpc.shutdown()
        raise ConfigurationError(
            f"Honest majority violated: threshold {threshold} >= {num_parties}/2"
        )

    # Secure integer type over finite field
    secint = mpc.SecInt(l=PRECISION_BITS)

    # Distribute shares: each party sends shares of its salary to all peers
    # mpc.input returns a list of 3 shares: [share_0, share_1, share_2]
    # Each party holds ONLY 1 share of each other party's secret.
    shares = mpc.input(secint(validated_salary))

    # Local homomorphic summation: [S]_j = [s_0]_j + [s_1]_j + [s_2]_j
    # No inter-party network communication occurs during addition.
    total_share = sum(shares)

    # Reconstruct ONLY the aggregate total sum.
    # Individual inputs s_0, s_1, s_2 are NEVER reconstructed.
    clear_sum_int = await mpc.output(total_share)
    total_sum = int(clear_sum_int)

    # Exact floating-point average calculation from the public aggregate
    average = float(total_sum) / float(num_parties)

    # Clean shutdown of MPyC runtime and sockets
    await mpc.shutdown()

    return {
        "party_id": mpc.pid,
        "parties_count": num_parties,
        "threshold": threshold,
        "aggregate_sum": total_sum,
        "average_salary": average,
    }
